from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import TickerRequest
from crew import run_analysis
import yfinance as yf
import json
import re

app = FastAPI(title="Stock Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tickers")
async def get_popular_tickers():
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX", "BRK-B", "JPM"]

@app.get("/api/stock/{ticker}/history")
async def get_stock_history(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "price": round(row["Close"], 2)
            })
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_stock(request: TickerRequest):
    try:
        raw_result = await run_analysis(request.ticker)
        
        # CrewAI 1.x result object has a 'raw' attribute
        clean_json = str(raw_result.raw if hasattr(raw_result, 'raw') else raw_result)
        
        # Remove markdown if present
        if "```json" in clean_json:
            clean_json = re.search(r"```json\n(.*?)\n```", clean_json, re.DOTALL).group(1)
        elif "```" in clean_json:
             clean_json = re.search(r"```\n(.*?)\n```", clean_json, re.DOTALL).group(1)
        
        parsed_result = json.loads(clean_json)
        return parsed_result
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
