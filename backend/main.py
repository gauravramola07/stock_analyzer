from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from crew import run_analysis
import yfinance as yf
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
import pandas as pd
import requests
from io import StringIO

app = FastAPI(title="Stock Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TICKER_CACHE = []


def load_all_tickers():
    global TICKER_CACHE

    if TICKER_CACHE:
        return TICKER_CACHE

    try:
        nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        nasdaq_text = requests.get(nasdaq_url, timeout=30).text

        nasdaq_df = pd.read_csv(
            StringIO(nasdaq_text),
            sep="|"
        )

        nasdaq_symbols = (
            nasdaq_df["Symbol"]
            .dropna()
            .astype(str)
            .tolist()
        )

        other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        other_text = requests.get(other_url, timeout=30).text

        other_df = pd.read_csv(
            StringIO(other_text),
            sep="|"
        )

        other_symbols = (
            other_df["ACT Symbol"]
            .dropna()
            .astype(str)
            .tolist()
        )

        tickers = sorted(
            list(
                set(
                    [
                        s.strip()
                        for s in nasdaq_symbols + other_symbols
                        if s and "." not in s and "$" not in s
                    ]
                )
            )
        )

        TICKER_CACHE = tickers
        return tickers

    except Exception as e:
        print(f"Ticker load error: {e}")
        return ["AAPL", "MSFT", "NVDA", "TSLA"]


@app.get("/api/tickers/search")
async def search_tickers(q: str = ""):
    tickers = load_all_tickers()

    if not q:
        return tickers

    q = q.upper()

    return [
        t for t in tickers
        if q in t
    ]


@app.get("/api/stock/{ticker}/history")
async def get_stock_history(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")

        if hist.empty:
            raise HTTPException(status_code=404, detail="No history found")

        data = [
            {"date": idx.strftime("%Y-%m-%d"), "price": round(float(row["Close"]), 2)}
            for idx, row in hist.iterrows()
            if row.get("Close") is not None
        ]

        info = stock.info or {}
        current = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        prev = info.get("previousClose") or current
        change = ((current - prev) / prev * 100) if prev else 0

        return {
            "history": data,
            "current_price": round(float(current), 2) if current is not None else 0,
            "day_change_pct": round(float(change), 2),
            "company_name": info.get("longName") or info.get("shortName") or ticker,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _extract_role(step_output) -> str:
    for attr in ("agent", "agent_role", "role", "name"):
        value = getattr(step_output, attr, None)
        if value:
            if isinstance(value, str):
                return value
            for nested in ("role", "name"):
                nested_value = getattr(value, nested, None)
                if nested_value:
                    return str(nested_value)
            return str(value)
    return "Agent"


@app.get("/api/analyze/stream/{ticker}")
async def stream_analysis(ticker: str):
    async def event_generator():
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def crew_callback(step_output):
            try:
                agent_name = _extract_role(step_output)

                phase_map = {
                    "Market Data Researcher": "data",
                    "Financial News Analyst": "news",
                    "Technical Analyst": "analysis",
                    "Chief Risk Officer": "risk",
                    "Senior Equity Analyst": "expert",
                }
                current_step = phase_map.get(agent_name, "data")

                phase_payload = json.dumps({"step": current_step, "status": "running"})
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "phase", "data": phase_payload})

                thought = "Processing data..."
                if hasattr(step_output, "thought") and step_output.thought:
                    thought = str(step_output.thought)[:80] + "..."
                elif hasattr(step_output, "tool"):
                    thought = f"Invoking function: {step_output.tool}..."

                msg = f"[{agent_name}] {thought}"
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "log", "data": msg})
            except Exception:
                pass

        analysis_task = asyncio.create_task(run_analysis(ticker, step_callback=crew_callback, log_queue=queue))

        while not analysis_task.done():
            try:
                msg_dict = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield msg_dict
            except asyncio.TimeoutError:
                continue

        try:
            result = await analysis_task
            yield {"event": "phase", "data": json.dumps({"step": "complete", "status": "done"})}
            yield {"event": "final_result", "data": result}
        except Exception as e:
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())


@app.get("/")
async def health():
    return {"status": "ok", "service": "Stock Intelligence API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)