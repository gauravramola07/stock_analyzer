import yfinance as yf
import asyncio
import requests_cache
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from utils import _to_iso_date, clean_json_data, _SESSION
import math

import time
from yfinance import data
data.HAS_CURL_CFFI = False

yf.set_tz_cache_location("yfinance_cache")

# Apply monkey patch to yfinance cookie/crumb fetcher to prevent rate limit storms
_LAST_CRUMB_ATTEMPT = 0
_CRUMB_COOLDOWN = 15.0  # 15 seconds cooldown between crumb fetch attempts if failing

original_get_cookie_and_crumb = data.YfData._get_cookie_and_crumb

def patched_get_cookie_and_crumb(self, timeout=30):
    if self._crumb is not None:
        return self._crumb, self._cookie_strategy
        
    global _LAST_CRUMB_ATTEMPT
    now = time.time()
    if now - _LAST_CRUMB_ATTEMPT < _CRUMB_COOLDOWN:
        return None, self._cookie_strategy
        
    _LAST_CRUMB_ATTEMPT = now
    
    max_attempts = 3
    backoff = 2.0
    for attempt in range(max_attempts):
        try:
            return original_get_cookie_and_crumb(self, timeout)
        except Exception as e:
            err_msg = str(e)
            is_rate_limit = (
                "429" in err_msg 
                or "rate limit" in err_msg.lower() 
                or "too many requests" in err_msg.lower()
                or "RateLimit" in type(e).__name__
            )
            if is_rate_limit and attempt < max_attempts - 1:
                sleep_time = backoff ** attempt
                print(f"[yfinance-patch] Cookie/crumb fetch rate-limited. Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                continue
            raise

data.YfData._get_cookie_and_crumb = patched_get_cookie_and_crumb

# Pre-warm cookie/crumb cache sequentially on startup
try:
    print("[prefetch] Pre-warming yfinance cookie/crumb cache...")
    _test_stock = yf.Ticker("AAPL", session=_SESSION)
    _ = _test_stock.history(period="1d")
    print("[prefetch] yfinance cookie/crumb cache pre-warmed successfully.")
except Exception as e:
    print(f"[prefetch] Warning: Failed to pre-warm cache: {e}")

# Global memory cache for prefetch data to avoid rate limits
_PREFETCH_CACHE = {}
_PREFETCH_CACHE_TTL = 1800  # 30 minutes cache

def _with_cache_and_retry(ticker: str, cache_key: str, fetch_fn):
    now = time.time()
    full_key = f"{ticker}:{cache_key}"
    
    # Check cache
    if full_key in _PREFETCH_CACHE:
        val, expiry = _PREFETCH_CACHE[full_key]
        if now < expiry:
            return val
            
    # Retry configuration
    max_retries = 5
    backoff_factor = 2.0
    last_err = None
    
    for attempt in range(max_retries):
        try:
            res = fetch_fn()
            # If the fetch returned an error representation, raise to trigger retry
            if isinstance(res, dict) and "error" in res:
                # If it's a rate limit error, raise to trigger retry
                if "rate limit" in res["error"].lower() or "too many requests" in res["error"].lower():
                    raise Exception(res["error"])
            
            # Cache the successful result
            _PREFETCH_CACHE[full_key] = (res, now + _PREFETCH_CACHE_TTL)
            return res
        except Exception as e:
            last_err = e
            err_msg = str(e)
            is_rate_limit = (
                "429" in err_msg 
                or "rate limit" in err_msg.lower() 
                or "too many requests" in err_msg.lower()
                or "RateLimit" in type(e).__name__
            )
            if is_rate_limit and attempt < max_retries - 1:
                sleep_time = backoff_factor ** attempt
                print(f"[prefetch] Rate limit hit for {full_key} (attempt {attempt+1}/{max_retries}). Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                continue
            elif attempt < max_retries - 1:
                time.sleep(1.0)
                continue
            else:
                break
                
    if last_err:
        raise last_err
    raise Exception(f"Failed to fetch {full_key}")


def _safe_get(df: pd.DataFrame, label: str, col) -> Any:
    if df is None or df.empty:
        return None
    if label not in df.index:
        return None
    if col not in df.columns:
        return None
    val = df.loc[label, col]
    if pd.isna(val):
        return None
    return float(val)


def _get_company_name_fallback(ticker: str) -> str:
    try:
        import os, json, tempfile
        ticker_file = os.path.join(tempfile.gettempdir(), "stock_analyzer_tickers.json")
        if os.path.exists(ticker_file):
            with open(ticker_file, "r") as f:
                mapping = json.load(f)
            if isinstance(mapping, dict) and ticker in mapping:
                return mapping[ticker]
    except Exception:
        pass
    return ticker


def fetch_stock_data(ticker: str) -> Dict[str, Any]:
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        try:
            info = stock.info or {}
        except Exception as e:
            print(f"[prefetch] Warning: Failed to fetch stock.info for {ticker}: {e}")
            info = {}

        fast = {}
        try:
            fast = stock.fast_info
        except Exception as fe:
            print(f"[prefetch] Warning: Failed to get fast_info for {ticker}: {fe}")

        current = info.get("currentPrice") or info.get("regularMarketPrice") or fast.get("lastPrice")
        if current is None or current == 0.0:
            try:
                hist = stock.history(period="1d")
                if not hist.empty:
                    current = float(hist["Close"].iloc[-1])
            except Exception:
                pass
        if current is None:
            current = 0.0

        prev = info.get("previousClose") or fast.get("previousClose") or current
        day_change_pct = ((current - prev) / prev * 100) if prev and current else 0
        quote_type = info.get("quoteType") or fast.get("quoteType") or "EQUITY"

        dividend_yield = info.get("dividendYield")
        if dividend_yield is None:
            dividend_yield = info.get("trailingAnnualDividendYield")
            if dividend_yield is not None:
                dividend_yield = float(dividend_yield) * 100.0

        # Fallback to compute dividend yield from dividends history
        if dividend_yield is None and current > 0:
            try:
                dividends = stock.dividends
                if not dividends.empty:
                    now_ts = pd.Timestamp.now(tz=dividends.index.tz)
                    one_year_ago = now_ts - pd.Timedelta(days=365)
                    last_year_divs = dividends[dividends.index >= one_year_ago]
                    if not last_year_divs.empty:
                        annual_div = float(last_year_divs.sum())
                        dividend_yield = (annual_div / current) * 100.0
            except Exception as div_err:
                print(f"[prefetch] Warning: Failed to calculate dividend yield fallback for {ticker}: {div_err}")

        # Fallback to compute trailingPE and epsTrailingTwelveMonths from financials & fast_info
        eps_trailing = info.get("epsTrailingTwelveMonths")
        pe_ratio = info.get("trailingPE")
        if (eps_trailing is None or pe_ratio is None) and current > 0:
            try:
                financials = stock.financials
                shares = fast.get("shares")
                if financials is not None and not financials.empty and shares and shares > 0:
                    net_income_labels = ["Net Income Common Stockholders", "Net Income"]
                    net_income_val = None
                    for label in net_income_labels:
                        if label in financials.index:
                            val = financials.loc[label].iloc[0]
                            if pd.notna(val):
                                net_income_val = float(val)
                                break
                    if net_income_val is not None:
                        eps_trailing = net_income_val / shares
                        if eps_trailing > 0:
                            pe_ratio = current / eps_trailing
            except Exception as fin_err:
                print(f"[prefetch] Warning: Failed to calculate PE ratio fallback for {ticker}: {fin_err}")

        # Fallback values from fast_info
        market_cap = info.get("marketCap") or fast.get("marketCap")
        fifty_two_high = info.get("fiftyTwoWeekHigh") or fast.get("yearHigh") or current
        fifty_two_low = info.get("fiftyTwoWeekLow") or fast.get("yearLow") or current
        volume = info.get("volume") or fast.get("lastVolume")
        average_volume = info.get("averageVolume") or fast.get("threeMonthAverageVolume")

        return {
            "quoteType": quote_type,
            "isETF": quote_type in ("ETF", "MUTUALFUND", "INDEX"),
            "currentPrice": current,
            "previousClose": prev,
            "dayChangePct": round(float(day_change_pct), 2) if day_change_pct else 0,
            "marketCap": market_cap,
            "trailingPE": pe_ratio,
            "forwardPE": info.get("forwardPE"),
            "priceToBook": info.get("priceToBook"),
            "priceToSalesTrailing12Months": info.get("priceToSalesTrailing12Months"),
            "beta": info.get("beta") or 1.0,  # default to 1.0 if missing
            "dividendYield": dividend_yield,
            "fiftyTwoWeekHigh": fifty_two_high,
            "fiftyTwoWeekLow": fifty_two_low,
            "volume": volume,
            "averageVolume": average_volume,
            "epsTrailingTwelveMonths": eps_trailing,
            "epsForward": info.get("epsForward"),
            "revenueGrowth": info.get("revenueGrowth"),
            "earningsGrowth": info.get("earningsGrowth"),
            "profitMargins": info.get("profitMargins"),
            "operatingMargins": f"{info.get('operatingMargins') * 100:.1f}%" if info.get('operatingMargins') is not None else None,
            "operatingMargins_raw": info.get("operatingMargins"),  # Keep raw for calculations
            "returnOnEquity": info.get("returnOnEquity"),
            "debtToEquity": float(info.get("debtToEquity")) if info.get("debtToEquity") is not None else None,
            "currentRatio": info.get("currentRatio"),
            "longBusinessSummary": info.get("longBusinessSummary", "N/A"),
            "shortName": info.get("shortName") or info.get("longName") or _get_company_name_fallback(ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "city": info.get("city", ""),
            "website": info.get("website", ""),
            "fullTimeEmployees": info.get("fullTimeEmployees"),
        }

    try:
        return _with_cache_and_retry(ticker, "stock_data", _fetch)
    except Exception as e:
        return {"error": f"Error fetching stock data: {str(e)}", "shortName": ticker}



def fetch_stock_history(ticker: str) -> List[Dict[str, Any]]:
    """Fetch 6-month price history for meaningful support/resistance levels."""
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        hist = stock.history(period="6mo", auto_adjust=False)
        if hist.empty:
            return []
        hist = hist.reset_index()
        date_column = "Date" if "Date" in hist.columns else hist.columns[0]
        if date_column in hist.columns:
            hist[date_column] = hist[date_column].dt.strftime("%Y-%m-%d")
        close_col = "Close" if "Close" in hist.columns else None
        volume_col = "Volume" if "Volume" in hist.columns else None
        if not close_col:
            return []
        return [
            {
                "date": row[date_column],
                "price": round(float(row[close_col]), 2),
                "volume": int(row[volume_col]) if volume_col and row.get(volume_col) is not None and math.isfinite(float(row[volume_col])) else None,
            }
            for _, row in hist.iterrows()
            if row.get(close_col) is not None and math.isfinite(float(row[close_col]))
        ]

    try:
        return _with_cache_and_retry(ticker, "stock_history", _fetch)
    except Exception:
        return []


def fetch_stock_news(ticker: str) -> List[Dict[str, Any]]:
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        news = getattr(stock, "news", []) or []
        
        # Get keywords for filtering relevance
        keywords = [ticker.lower()]
        try:
            info = stock.info or {}
            company_name = info.get("shortName") or info.get("longName") or ""
            if company_name:
                # Remove common corporate suffixes like Inc., Corp., Co., Ltd., Class A, etc.
                clean_name = company_name.replace("Inc.", "").replace("Corp.", "").replace("Corporation", "").replace("Co.", "").replace("Ltd.", "").strip()
                parts = [p.lower() for p in clean_name.split() if len(p) > 2]
                if parts:
                    keywords.append(parts[0])
        except Exception:
            pass

        scored_articles = []
        for item in news:
            content = item.get("content", item) if isinstance(item, dict) else {}
            if not isinstance(content, dict):
                content = item
            published = content.get("providerPublishTime") or content.get("pubDate")
            title = content.get("title", "")
            summary = content.get("summary", "")
            if not title and not summary:
                continue

            # Filter relevance by checking keywords in title or summary
            title_lower = title.lower()
            summary_lower = summary.lower()
            
            has_kw_title = any(kw in title_lower for kw in keywords)
            has_kw_summary = any(kw in summary_lower for kw in keywords)
            
            if not (has_kw_title or has_kw_summary):
                continue

            # Score relevance
            score = 0
            if has_kw_title:
                score += 10
            if has_kw_summary:
                score += 3

            # Extract source
            provider = content.get("provider")
            if isinstance(provider, dict):
                source = provider.get("displayName") or provider.get("publisher") or provider.get("source") or "Unknown"
            else:
                source = content.get("publisher") or content.get("source") or "Unknown"

            # Extract URL
            canonical = content.get("canonicalUrl")
            click_through = content.get("clickThroughUrl")
            if isinstance(canonical, dict):
                url = canonical.get("url")
            elif isinstance(click_through, dict):
                url = click_through.get("url")
            else:
                url = content.get("link")

            # Formatting published date
            date_str = _to_iso_date(published)
            if "T" in date_str:
                date_str = date_str.split("T")[0]

            scored_articles.append((score, {
                "title": title or "Untitled",
                "source": source,
                "date": date_str,
                "url": url,
                "summary": summary or title or "No summary available.",
                "sentiment": "Neutral",
            }))
            
        # Sort by score descending
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return [art for _, art in scored_articles[:8]]

    try:
        return _with_cache_and_retry(ticker, "stock_news", _fetch)
    except Exception:
        return []


def fetch_analyst_data(ticker: str) -> Dict[str, Any]:
    """Fetch analyst price targets and recommendation summary from yfinance."""
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        try:
            info = stock.info or {}
        except Exception as e:
            print(f"[prefetch] Warning: Failed to fetch analyst stock.info for {ticker}: {e}")
            info = {}

        result = {
            "mean_target": info.get("targetMeanPrice"),
            "high_target": info.get("targetHighPrice"),
            "low_target": info.get("targetLowPrice"),
            "median_target": info.get("targetMedianPrice"),
            "num_analysts": info.get("numberOfAnalystOpinions"),
            "recommendation_key": info.get("recommendationKey"),  # e.g. "buy", "hold"
            "recommendation_mean": info.get("recommendationMean"),  # 1=Strong Buy, 5=Strong Sell
            "strong_buy": None,
            "buy": None,
            "hold": None,
            "sell": None,
            "strong_sell": None,
        }

        # Analyst count breakdown from recommendations_summary if available
        try:
            rec_summary = stock.recommendations_summary
            if rec_summary is not None and not rec_summary.empty:
                latest = rec_summary.iloc[0]
                result["strong_buy"] = int(latest.get("strongBuy", 0)) if not pd.isna(latest.get("strongBuy", 0)) else None
                result["buy"] = int(latest.get("buy", 0)) if not pd.isna(latest.get("buy", 0)) else None
                result["hold"] = int(latest.get("hold", 0)) if not pd.isna(latest.get("hold", 0)) else None
                result["sell"] = int(latest.get("sell", 0)) if not pd.isna(latest.get("sell", 0)) else None
                result["strong_sell"] = int(latest.get("strongSell", 0)) if not pd.isna(latest.get("strongSell", 0)) else None
        except Exception:
            pass
        return result

    try:
        return _with_cache_and_retry(ticker, "analyst_data", _fetch)
    except Exception as e:
        print(f"[prefetch] analyst_data error for {ticker}: {e}")
        return {
            "mean_target": None,
            "high_target": None,
            "low_target": None,
            "median_target": None,
            "num_analysts": None,
            "recommendation_key": None,
            "recommendation_mean": None,
            "strong_buy": None,
            "buy": None,
            "hold": None,
            "sell": None,
            "strong_sell": None,
        }


def fetch_technical_indicators(ticker: str) -> Dict[str, Any]:
    """
    Pre-compute key technical indicators from 6-month history.
    Returns SMA-20, SMA-50, RSI-14, MACD line/signal, and Bollinger Bands.
    Computing these here (not in the LLM) eliminates hallucination risk.
    """
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        hist = stock.history(period="6mo", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return {
                "sma_20": None, "sma_50": None, "rsi_14": None,
                "macd_line": None, "macd_signal": None, "macd_histogram": None,
                "macd_crossover": None, "bb_upper": None, "bb_lower": None, "bb_position": None,
                "price_vs_sma20": None, "price_vs_sma50": None, "rsi_signal": None,
                "fifty_two_week_position": None, "avg_volume_ratio": None, "volatility_30d": None
            }

        closes = hist["Close"].dropna()
        if len(closes) < 14:
            print(f"[prefetch] Insufficient price history for {ticker} ({len(closes)} points) — skipping indicators")
            raise Exception("Insufficient price history")

        result = {
            "sma_20": None,
            "sma_50": None,
            "rsi_14": None,
            "macd_line": None,
            "macd_signal": None,
            "macd_histogram": None,
            "macd_crossover": None,  # "Bullish" | "Bearish" | "Neutral"
            "bb_upper": None,
            "bb_lower": None,
            "bb_position": None,  # % position within bands (0=lower, 1=upper)
            "price_vs_sma20": None,  # "above" | "below"
            "price_vs_sma50": None,
            "rsi_signal": None,  # "Overbought" | "Oversold" | "Neutral"
            "fifty_two_week_position": None,  # % between 52-wk low and high
            "avg_volume_ratio": None,  # today's volume vs 20d avg
            "volatility_30d": None,
        }

        # SMA
        if len(closes) >= 20:
            result["sma_20"] = round(float(closes.rolling(20).mean().iloc[-1]), 2)
        if len(closes) >= 50:
            result["sma_50"] = round(float(closes.rolling(50).mean().iloc[-1]), 2)

        current_price = float(closes.iloc[-1])

        if result["sma_20"]:
            result["price_vs_sma20"] = "above" if current_price > result["sma_20"] else "below"
        if result["sma_50"]:
            result["price_vs_sma50"] = "above" if current_price > result["sma_50"] else "below"

        # RSI-14
        delta = closes.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = float(rsi.iloc[-1])
        result["rsi_14"] = round(rsi_val, 2)
        if rsi_val >= 70:
            result["rsi_signal"] = "Overbought"
        elif rsi_val <= 30:
            result["rsi_signal"] = "Oversold"
        else:
            result["rsi_signal"] = "Neutral"

        # MACD (12, 26, 9)
        ema12 = closes.ewm(span=12, adjust=False).mean()
        ema26 = closes.ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26
        macd_signal = macd_line.ewm(span=9, adjust=False).mean()
        macd_hist = macd_line - macd_signal

        result["macd_line"] = round(float(macd_line.iloc[-1]), 4)
        result["macd_signal"] = round(float(macd_signal.iloc[-1]), 4)
        result["macd_histogram"] = round(float(macd_hist.iloc[-1]), 4)

        # Detect crossover (last 3 bars)
        if len(macd_hist) >= 3:
            prev_hist = float(macd_hist.iloc[-2])
            curr_hist = float(macd_hist.iloc[-1])
            if prev_hist < 0 and curr_hist > 0:
                result["macd_crossover"] = "Bullish"
            elif prev_hist > 0 and curr_hist < 0:
                result["macd_crossover"] = "Bearish"
            else:
                result["macd_crossover"] = "Neutral"

        # Bollinger Bands (20, 2)
        sma20_series = closes.rolling(20).mean()
        std20 = closes.rolling(20).std()
        bb_upper = sma20_series + 2 * std20
        bb_lower = sma20_series - 2 * std20
        bb_u = float(bb_upper.iloc[-1])
        bb_l = float(bb_lower.iloc[-1])
        result["bb_upper"] = round(bb_u, 2)
        result["bb_lower"] = round(bb_l, 2)
        band_width = bb_u - bb_l
        if band_width > 0:
            result["bb_position"] = round((current_price - bb_l) / band_width, 3)

        # Volume ratio
        if "Volume" in hist.columns:
            volumes = hist["Volume"].dropna()
            if len(volumes) >= 20:
                avg_vol = float(volumes.rolling(20).mean().iloc[-1])
                today_vol = float(volumes.iloc[-1])
                if avg_vol > 0:
                    result["avg_volume_ratio"] = round(today_vol / avg_vol, 2)

        # 52-week position
        try:
            info = stock.info or {}
        except Exception as e:
            print(f"[prefetch] Warning: Failed to fetch technical stock.info for {ticker}: {e}")
            info = {}
        high_52 = info.get("fiftyTwoWeekHigh")
        low_52 = info.get("fiftyTwoWeekLow")
        if high_52 and low_52 and (high_52 - low_52) > 0:
            result["fifty_two_week_position"] = round(
                (current_price - low_52) / (high_52 - low_52), 3
            )

        # Volatility (30-day annualized)
        if len(closes) >= 30:
            returns = closes.pct_change().dropna()
            std_30d = returns.tail(30).std()
            annualized_vol = std_30d * np.sqrt(252)
            result["volatility_30d"] = round(float(annualized_vol), 4)
        elif len(closes) > 1:
            returns = closes.pct_change().dropna()
            std_all = returns.std()
            annualized_vol = std_all * np.sqrt(252)
            result["volatility_30d"] = round(float(annualized_vol), 4)
        else:
            result["volatility_30d"] = 0.0
        return result

    try:
        return _with_cache_and_retry(ticker, "technical_indicators", _fetch)
    except Exception as e:
        print(f"[prefetch] technical_indicators error for {ticker}: {e}")
        return {
            "sma_20": None, "sma_50": None, "rsi_14": None,
            "macd_line": None, "macd_signal": None, "macd_histogram": None,
            "macd_crossover": None, "bb_upper": None, "bb_lower": None, "bb_position": None,
            "price_vs_sma20": None, "price_vs_sma50": None, "rsi_signal": None,
            "fifty_two_week_position": None, "avg_volume_ratio": None, "volatility_30d": None
        }


def fetch_financial_data(ticker: str) -> Dict[str, Any]:
    def _fetch():
        stock = yf.Ticker(ticker, session=_SESSION)
        financials = stock.financials
        balance_sheet = stock.balance_sheet
        cashflow = stock.cashflow

        records = []

        if financials is not None and not financials.empty:
            periods = financials.columns[:4]
            for col in periods:
                period_str = col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
                record = {
                    "period": period_str,
                    "source": "SEC EDGAR / yfinance",
                    "revenue": _safe_get(financials, "Total Revenue", col),
                    "net_income": _safe_get(financials, "Net Income", col),
                    "gross_profit": _safe_get(financials, "Gross Profit", col),
                    "total_assets": _safe_get(balance_sheet, "Total Assets", col) if balance_sheet is not None and not balance_sheet.empty else None,
                    "total_debt": _safe_get(balance_sheet, "Total Debt", col) if balance_sheet is not None and not balance_sheet.empty else None,
                    "operating_cash_flow": _safe_get(cashflow, "Operating Cash Flow", col) if cashflow is not None and not cashflow.empty else None,
                }
                records.append(record)

        return {"records": records}

    try:
        return _with_cache_and_retry(ticker, "financial_data", _fetch)
    except Exception:
        return {"records": []}


async def prefetch_all(ticker: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    
    # Check if we have cached results for all steps to avoid sequential delay
    keys = ["stock_data", "stock_history", "stock_news", "financial_data", "analyst_data", "technical_indicators"]
    now = time.time()
    all_cached = True
    for k in keys:
        cache_key = f"{ticker}:{k}"
        if cache_key not in _PREFETCH_CACHE or now >= _PREFETCH_CACHE[cache_key][1]:
            all_cached = False
            break
            
    if all_cached:
        # Fetch concurrently from memory (instantaneous)
        data_coro = loop.run_in_executor(None, fetch_stock_data, ticker)
        history_coro = loop.run_in_executor(None, fetch_stock_history, ticker)
        news_coro = loop.run_in_executor(None, fetch_stock_news, ticker)
        financial_coro = loop.run_in_executor(None, fetch_financial_data, ticker)
        analyst_coro = loop.run_in_executor(None, fetch_analyst_data, ticker)
        indicators_coro = loop.run_in_executor(None, fetch_technical_indicators, ticker)
        
        stock_data, history, news, financial_data, analyst_data, technical_indicators = await asyncio.gather(
            data_coro, history_coro, news_coro, financial_coro, analyst_coro, indicators_coro
        )
    else:
        # Sequential execution with sleep to prevent Yahoo rate limits on cache misses
        stock_data = await loop.run_in_executor(None, fetch_stock_data, ticker)
        await asyncio.sleep(0.1)
        history = await loop.run_in_executor(None, fetch_stock_history, ticker)
        await asyncio.sleep(0.1)
        news = await loop.run_in_executor(None, fetch_stock_news, ticker)
        await asyncio.sleep(0.1)
        financial_data = await loop.run_in_executor(None, fetch_financial_data, ticker)
        await asyncio.sleep(0.1)
        analyst_data = await loop.run_in_executor(None, fetch_analyst_data, ticker)
        await asyncio.sleep(0.1)
        technical_indicators = await loop.run_in_executor(None, fetch_technical_indicators, ticker)

    res = {
        "stock_data": stock_data,
        "history": history,
        "news": news,
        "financial_data": financial_data,
        "analyst_data": analyst_data,
        "technical_indicators": technical_indicators,
    }
    return clean_json_data(res)