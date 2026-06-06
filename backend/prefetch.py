import yfinance as yf
import asyncio
import requests_cache
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timezone

requests_cache.install_cache("yfinance_cache", expire_after=3600)


def _to_iso_date(value: Any) -> str:
    if value is None:
        return ""
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        pass
    return str(value)


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


def fetch_stock_data(ticker: str) -> Dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        dividend_yield = info.get("dividendYield")
        if dividend_yield is None:
            dividend_yield = info.get("trailingAnnualDividendYield")
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        prev = info.get("previousClose") or current
        day_change_pct = ((current - prev) / prev * 100) if prev and current else 0
        return {
            "currentPrice": current,
            "previousClose": prev,
            "dayChangePct": round(float(day_change_pct), 2) if day_change_pct else 0,
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "beta": info.get("beta"),
            "dividendYield": dividend_yield,
            "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "longBusinessSummary": info.get("longBusinessSummary", "N/A"),
            "shortName": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "country": info.get("country", ""),
            "city": info.get("city", ""),
            "website": info.get("website", ""),
            "fullTimeEmployees": info.get("fullTimeEmployees"),
        }
    except Exception as e:
        return {"error": f"Error fetching stock data: {str(e)}", "shortName": ticker}


def fetch_stock_history(ticker: str) -> List[Dict[str, Any]]:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo", auto_adjust=False)
        if hist.empty:
            return []
        hist = hist.reset_index()
        date_column = "Date" if "Date" in hist.columns else hist.columns[0]
        if date_column in hist.columns:
            hist[date_column] = hist[date_column].dt.strftime("%Y-%m-%d")
        close_col = "Close" if "Close" in hist.columns else None
        if not close_col:
            return []
        return [
            {"date": row[date_column], "price": round(float(row[close_col]), 2)}
            for _, row in hist.iterrows()
            if row.get(close_col) is not None
        ]
    except Exception:
        return []


def fetch_stock_news(ticker: str) -> List[Dict[str, Any]]:
    try:
        stock = yf.Ticker(ticker)
        news = getattr(stock, "news", []) or []
        cleaned = []
        for item in news[:10]:
            published = item.get("providerPublishTime") or item.get("pubDate")
            title = item.get("title", "")
            summary = item.get("summary", "")
            if not title and not summary:
                continue
            cleaned.append({
                "title": title or "Untitled",
                "source": item.get("publisher") or item.get("source") or "Unknown",
                "date": _to_iso_date(published),
                "url": item.get("link"),
                "summary": summary or title or "No summary available.",
                "sentiment": "Neutral",
            })
        return cleaned
    except Exception:
        return []


def fetch_financial_data(ticker: str) -> Dict[str, Any]:
    try:
        stock = yf.Ticker(ticker)
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
    except Exception:
        return {"records": []}


async def prefetch_all(ticker: str) -> Dict[str, Any]:
    loop = asyncio.get_running_loop()
    data_coro = loop.run_in_executor(None, fetch_stock_data, ticker)
    history_coro = loop.run_in_executor(None, fetch_stock_history, ticker)
    news_coro = loop.run_in_executor(None, fetch_stock_news, ticker)
    financial_coro = loop.run_in_executor(None, fetch_financial_data, ticker)
    stock_data, history, news, financial_data = await asyncio.gather(
        data_coro, history_coro, news_coro, financial_coro
    )
    return {
        "stock_data": stock_data,
        "history": history,
        "news": news,
        "financial_data": financial_data,
    }