import yfinance as yf
from crewai.tools import BaseTool
from pydantic import Field
from typing import Dict, Any, List
from langchain_community.tools import DuckDuckGoSearchRun

class StockDataTool(BaseTool):
    name: str = "fetch_stock_data"
    description: str = "Fetch real-time price and fundamental metrics for a given stock ticker."

    def _run(self, ticker: str) -> Dict[str, Any]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "beta": info.get("beta"),
                "longBusinessSummary": info.get("longBusinessSummary", "N/A")
            }
        except Exception as e:
            return {"error": f"Error: {str(e)}"}

class StockHistoryTool(BaseTool):
    name: str = "fetch_stock_history"
    description: str = "Fetch historical price data for the last 30 days."

    def _run(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            hist.reset_index(inplace=True)
            hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')
            return hist[['Date', 'Close']].to_dict(orient='records')
        except Exception as e:
            return [{"error": str(e)}]

class StockNewsTool(BaseTool):
    name: str = "fetch_stock_news"
    description: str = "Fetch recent news articles for a given stock ticker."

    def _run(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            stock = yf.Ticker(ticker)
            return stock.news[:10]
        except Exception as e:
            return [{"error": str(e)}]

class SearchTool(BaseTool):
    name: str = "internet_search"
    description: str = "Search the internet for the latest news and information about a stock or company."

    def _run(self, query: str) -> str:
        try:
            search = DuckDuckGoSearchRun()
            return search.run(query)
        except Exception as e:
            return f"Search error: {str(e)}"

# Instantiate the tools
fetch_stock_data = StockDataTool()
fetch_stock_history = StockHistoryTool()
fetch_stock_news = StockNewsTool()
search_tool = SearchTool()
