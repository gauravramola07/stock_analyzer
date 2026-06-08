import yfinance as yf
from crewai.tools import BaseTool
from typing import Dict, Any, List
from utils import _to_iso_date

try:
    from langchain_community.tools import DuckDuckGoSearchRun
except ImportError:  # pragma: no cover
    from langchain_community.tools.ddg_search.tool import DuckDuckGoSearchRun


# NOTE: Caching is managed centrally by prefetch.py via CachedSession.
# Do NOT call requests_cache.install_cache() here — it conflicts with prefetch.py.


class StockDataTool(BaseTool):
    name: str = "fetch_stock_data"
    description: str = "Fetch real-time price and fundamental metrics for a stock ticker."

    def _run(self, ticker: str) -> Dict[str, Any]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            dividend_yield = info.get("dividendYield")
            if dividend_yield is None:
                dividend_yield = info.get("trailingAnnualDividendYield")

            return {
                "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "beta": info.get("beta"),
                "dividendYield": dividend_yield,
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "volume": info.get("volume"),
                "longBusinessSummary": info.get("longBusinessSummary", "N/A"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "shortName": info.get("shortName") or info.get("longName") or ticker,
            }
        except Exception as e:
            return {"error": f"Error fetching stock data: {str(e)}"}


class StockHistoryTool(BaseTool):
    name: str = "fetch_stock_history"
    description: str = "Fetch historical price data for the last 30 days."

    def _run(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo", auto_adjust=False)

            if hist.empty:
                return [{"error": "No historical data found"}]

            hist = hist.reset_index()

            date_column = "Date" if "Date" in hist.columns else hist.columns[0]
            if date_column in hist.columns:
                hist[date_column] = hist[date_column].dt.strftime("%Y-%m-%d")

            close_col = "Close" if "Close" in hist.columns else None
            if not close_col:
                return [{"error": "Historical data did not include Close prices"}]

            return [
                {"date": row[date_column], "price": round(float(row[close_col]), 2)}
                for _, row in hist.iterrows()
                if row.get(close_col) is not None
            ]
        except Exception as e:
            return [{"error": str(e)}]


class StockNewsTool(BaseTool):
    name: str = "fetch_stock_news"
    description: str = "Fetch the most recent news articles for a given stock ticker."

    def _run(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            stock = yf.Ticker(ticker)
            news = getattr(stock, "news", []) or []
            cleaned: List[Dict[str, Any]] = []

            for item in news[:10]:
                published = item.get("providerPublishTime") or item.get("pubDate")
                cleaned.append(
                    {
                        "title": item.get("title"),
                        "source": item.get("publisher") or item.get("source"),
                        "date": _to_iso_date(published),
                        "url": item.get("link"),
                        "summary": item.get("summary") or "",
                        "sentiment": "Neutral",
                    }
                )

            return cleaned or [{"error": "No recent news found"}]
        except Exception as e:
            return [{"error": str(e)}]


class SearchTool(BaseTool):
    name: str = "internet_search"
    description: str = "Search the internet for the latest macroeconomic news or company specifics."

    def _run(self, query: str) -> str:
        try:
            search = DuckDuckGoSearchRun()
            return search.run(query)
        except Exception as e:
            return f"Search error: {str(e)}"


fetch_stock_data = StockDataTool()
fetch_stock_history = StockHistoryTool()
fetch_stock_news = StockNewsTool()
search_tool = SearchTool()