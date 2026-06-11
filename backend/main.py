from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from crew import run_analysis
from sse_starlette.event import ServerSentEvent
import yfinance as yf
from yfinance import data
data.HAS_CURL_CFFI = False
import json
import asyncio
import time
import os
import tempfile
import math
from contextlib import asynccontextmanager
from sse_starlette.sse import EventSourceResponse
import pandas as pd
import requests
from io import StringIO
from utils import clean_float, clean_json_data, _SESSION


TICKER_FILE = os.path.join(tempfile.gettempdir(), "stock_analyzer_tickers.json")
TICKER_CACHE = []
RESULT_CACHE = {}
RESULT_CACHE_TTL = 3600
HISTORY_CACHE = {}
HISTORY_CACHE_TTL = 300  # 5 minutes cache

# ---------------------------------------------------------------------------
# In-flight deduplication: one pipeline per ticker, N SSE subscribers.
# Each RunningAnalysis holds an append-only event log so late-joining or
# reconnecting subscribers can replay buffered events before tailing live.
# ---------------------------------------------------------------------------
class RunningAnalysis:
    def __init__(self):
        self.events: list = []          # append-only [{event, data}]
        self.done: bool = False
        self.result: str | None = None
        self.error: str | None = None
        self._new_event = asyncio.Event()  # set briefly when events arrive

    def push(self, event_dict: dict):
        self.events.append(event_dict)
        self._new_event.set()

    def finish(self, result: str):
        self.result = result
        self.done = True
        self._new_event.set()

    def fail(self, error: str):
        self.error = error
        self.done = True
        self._new_event.set()

    async def wait_for_events(self):
        """Async-wait until new events are pushed (or analysis completes)."""
        self._new_event.clear()
        await self._new_event.wait()


RUNNING: dict[str, RunningAnalysis] = {}


def _fetch_tickers_from_sources():
    """Fetch all tickers from NASDAQ trader + additional sources."""
    all_tickers = {}

    try:
        nasdaq_url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        nasdaq_text = requests.get(nasdaq_url, timeout=30).text
        nasdaq_df = pd.read_csv(StringIO(nasdaq_text), sep="|")
        
        for _, row in nasdaq_df.iterrows():
            sym = str(row.get("Symbol", "")).strip()
            name = str(row.get("Security Name", "")).strip()
            if sym and name and not sym.startswith("File Creation Time") and "." not in sym and "$" not in sym and len(sym) <= 6:
                clean_name = name.split(" - ")[0].strip()
                all_tickers[sym] = clean_name
    except Exception as e:
        print(f"NASDAQ fetch error: {e}")

    try:
        other_url = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        other_text = requests.get(other_url, timeout=30).text
        other_df = pd.read_csv(StringIO(other_text), sep="|")
        
        for _, row in other_df.iterrows():
            sym = str(row.get("ACT Symbol", "")).strip()
            name = str(row.get("Security Name", "")).strip()
            if sym and name and not sym.startswith("File Creation Time") and "." not in sym and "$" not in sym and len(sym) <= 6:
                clean_name = name.split(" - ")[0].strip()
                all_tickers[sym] = clean_name
    except Exception as e:
        print(f"Otherlisted fetch error: {e}")

    return all_tickers


def _save_tickers_to_file(tickers):
    """Persist ticker dictionary to a local temp file."""
    try:
        with open(TICKER_FILE, "w") as f:
            json.dump(tickers, f)
        print(f"Saved {len(tickers)} tickers to {TICKER_FILE}")
    except Exception as e:
        print(f"Error saving ticker file: {e}")


def _load_tickers_from_file():
    """Load ticker dictionary from the local temp file."""
    try:
        if os.path.exists(TICKER_FILE):
            with open(TICKER_FILE, "r") as f:
                tickers = json.load(f)
            if tickers and len(tickers) > 100:
                print(f"Loaded {len(tickers)} tickers from {TICKER_FILE}")
                return tickers
    except Exception as e:
        print(f"Error loading ticker file: {e}")
    return None


def load_all_tickers():
    """Return all tickers — from memory cache, temp file, or fresh fetch."""
    global TICKER_CACHE

    if TICKER_CACHE:
        return TICKER_CACHE

    file_tickers = _load_tickers_from_file()
    if file_tickers:
        TICKER_CACHE = [
            {"symbol": sym, "name": name}
            for sym, name in sorted(file_tickers.items())
        ]
        return TICKER_CACHE

    tickers = _fetch_tickers_from_sources()
    if tickers:
        TICKER_CACHE = [
            {"symbol": sym, "name": name}
            for sym, name in sorted(tickers.items())
        ]
        _save_tickers_to_file(tickers)
    else:
        fallback_symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META",
                            "AMD", "NFLX", "CRM", "ADBE", "PYPL", "UBER", "COIN",
                            "INTC", "DIS", "BA", "JPM", "V", "MA", "WMT", "KO",
                            "PEP", "PFE", "JNJ", "XOM", "CVX", "GS", "IBM", "ORCL"]
        fallback_names = {
            "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "NVDA": "NVIDIA Corporation",
            "TSLA": "Tesla, Inc.", "AMZN": "Amazon.com, Inc.", "GOOGL": "Alphabet Inc.",
            "META": "Meta Platforms, Inc.", "AMD": "Advanced Micro Devices, Inc.", "NFLX": "Netflix, Inc.",
            "CRM": "Salesforce, Inc.", "ADBE": "Adobe Inc.", "PYPL": "PayPal Holdings, Inc.",
            "UBER": "Uber Technologies, Inc.", "COIN": "Coinbase Global, Inc.", "INTC": "Intel Corporation",
            "DIS": "The Walt Disney Company", "BA": "The Boeing Company", "JPM": "JPMorgan Chase & Co.",
            "V": "Visa Inc.", "MA": "Mastercard Incorporated", "WMT": "Walmart Inc.",
            "KO": "The Coca-Cola Company", "PEP": "PepsiCo, Inc.", "PFE": "Pfizer Inc.",
            "JNJ": "Johnson & Johnson", "XOM": "Exxon Mobil Corporation", "CVX": "Chevron Corporation",
            "GS": "The Goldman Sachs Group, Inc.", "IBM": "International Business Machines Corporation",
            "ORCL": "Oracle Corporation"
        }
        TICKER_CACHE = [
            {"symbol": s, "name": fallback_names.get(s, s)}
            for s in fallback_symbols
        ]

    return TICKER_CACHE


def get_company_name_from_cache(ticker: str) -> str:
    """Lookup company name from loaded ticker cache."""
    for item in TICKER_CACHE:
        if item["symbol"].upper() == ticker.upper():
            return item["name"]
    return ticker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load all tickers on startup and save to temp file."""
    print("🚀 Starting up — pre-loading all tickers...")
    load_all_tickers()
    print(f"✅ {len(TICKER_CACHE)} tickers ready.")
    yield
    print("🛑 Shutting down.")


app = FastAPI(title="Stock Intelligence API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/tickers")
async def get_all_tickers():
    """Return the complete ticker list with metadata."""
    tickers = load_all_tickers()
    return {
        "count": len(tickers),
        "tickers": tickers,
        "source": "cached" if TICKER_CACHE else "fetched",
    }


@app.get("/api/tickers/search")
async def search_tickers(q: str = "", limit: int = 0):
    """Search tickers by symbol or name. limit=0 means return all matches."""
    tickers = load_all_tickers()

    if not q:
        return tickers

    q = q.upper()
    matches = [
        t for t in tickers
        if q in t["symbol"].upper() or q in t["name"].upper()
    ]

    if limit and limit > 0:
        return matches[:limit]

    return matches


@app.get("/api/stock/{ticker}/history")
def get_stock_history(ticker: str):
    now = time.time()
    if ticker in HISTORY_CACHE:
        cached_data, expiry = HISTORY_CACHE[ticker]
        if now < expiry:
            return cached_data

    max_retries = 5
    backoff_factor = 2.0
    last_err = None

    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker, session=_SESSION)
            hist = stock.history(period="1mo")

            if hist.empty:
                raise HTTPException(status_code=404, detail="No history found")

            data = [
                {"date": idx.strftime("%Y-%m-%d"), "price": round(float(row["Close"]), 2)}
                for idx, row in hist.iterrows()
                if row.get("Close") is not None and math.isfinite(float(row["Close"]))
            ]

            try:
                info = stock.info or {}
            except Exception as e:
                print(f"[main] Warning: Failed to fetch stock.info for {ticker}: {e}")
                info = {}

            current = info.get("currentPrice") or info.get("regularMarketPrice")
            if current is None and len(data) > 0:
                current = data[-1]["price"]
                
            prev = info.get("previousClose")
            if prev is None and len(data) > 1:
                prev = data[-2]["price"]
            elif prev is None:
                prev = current
                
            current_val = clean_float(current, 0.0)
            prev_val = clean_float(prev, current_val)
            
            change = ((current_val - prev_val) / prev_val * 100) if prev_val else 0.0
            change_val = clean_float(change, 0.0)

            result = {
                "history": data,
                "current_price": round(current_val, 2),
                "day_change_pct": round(change_val, 2),
                "company_name": info.get("longName") or info.get("shortName") or get_company_name_from_cache(ticker),
            }
            result = clean_json_data(result)
            HISTORY_CACHE[ticker] = (result, now + HISTORY_CACHE_TTL)
            return result
        except HTTPException:
            raise
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
                print(f"[main] Rate limit hit for history of {ticker}. Retrying in {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                continue
            elif attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            else:
                break

    # If it failed after retries, determine appropriate exception
    err_msg = str(last_err)
    if (
        "429" in err_msg
        or "rate limit" in err_msg.lower()
        or "too many requests" in err_msg.lower()
        or "RateLimit" in type(last_err).__name__
    ):
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests. Rate limited. Try after a while."
        )
    raise HTTPException(status_code=500, detail=str(last_err))


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


def _start_analysis_task(ticker: str, run: RunningAnalysis):
    """
    Launch the analysis pipeline as a background asyncio task.
    All events are pushed into `run` (the shared broadcast object).
    This function is called ONCE per ticker — subsequent SSE connections
    just subscribe to the same `run` object.
    """
    loop = asyncio.get_running_loop()
    log_queue: asyncio.Queue = asyncio.Queue()

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
            step = phase_map.get(agent_name, "data")
            loop.call_soon_threadsafe(
                log_queue.put_nowait,
                {"event": "phase", "data": json.dumps({"step": step, "status": "running"})},
            )
            thought = "Processing data..."
            if hasattr(step_output, "thought") and step_output.thought:
                thought = str(step_output.thought)[:80] + "..."
            elif hasattr(step_output, "tool"):
                thought = f"Invoking function: {step_output.tool}..."
            loop.call_soon_threadsafe(
                log_queue.put_nowait,
                {"event": "log", "data": f"[{agent_name}] {thought}"},
            )
        except Exception:
            pass

    async def _run():
        analysis_task = asyncio.create_task(
            run_analysis(ticker, step_callback=crew_callback, log_queue=log_queue)
        )

        # Drain log_queue into run.events while analysis is running
        async def _drain():
            while not analysis_task.done():
                try:
                    msg = await asyncio.wait_for(log_queue.get(), timeout=1.0)
                    run.push(msg)
                except asyncio.TimeoutError:
                    continue
            # Drain remaining after task ends
            while not log_queue.empty():
                try:
                    run.push(log_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break

        drain_task = asyncio.create_task(_drain())

        try:
            result = await analysis_task
            await drain_task
            RESULT_CACHE[ticker] = {"result": result, "timestamp": time.time()}
            run.push({"event": "phase", "data": json.dumps({"step": "complete", "status": "done"})})
            run.finish(result)
            print(f"[stream] Analysis complete for {ticker} — {len(run.events)} events buffered")
        except Exception as e:
            await drain_task
            print(f"[stream] Analysis failed for {ticker}: {e}")
            run.fail(str(e))
        finally:
            RUNNING.pop(ticker, None)

    asyncio.create_task(_run())


@app.get("/api/analyze/stream/{ticker}")
async def stream_analysis(ticker: str):
    # 1. Serve completed result from cache instantly
    cached = RESULT_CACHE.get(ticker)
    if cached and time.time() - cached["timestamp"] < RESULT_CACHE_TTL:
        async def cached_generator():
            yield {"event": "phase", "data": json.dumps({"step": "complete", "status": "done"})}
            yield {"event": "final_result", "data": cached["result"]}
        return EventSourceResponse(cached_generator())

    # 2. Attach to existing in-flight analysis OR start a fresh one
    if ticker not in RUNNING:
        print(f"[stream] Starting new analysis for {ticker}")
        run = RunningAnalysis()
        RUNNING[ticker] = run
        _start_analysis_task(ticker, run)
    else:
        buffered = len(RUNNING[ticker].events)
        print(f"[stream] Subscriber joined existing run for {ticker} ({buffered} events already buffered)")

    run = RUNNING[ticker]

    # 3. Fan-out SSE: replay all buffered events, then tail until done
    async def event_generator():
        cursor = 0  # next index in run.events not yet sent to this subscriber

        while True:
            # Replay any buffered events this subscriber hasn't received yet
            while cursor < len(run.events):
                yield run.events[cursor]
                cursor += 1

            # If the pipeline is done, deliver the final outcome and stop
            if run.done:
                if run.result:
                    yield {"event": "final_result", "data": run.result}
                elif run.error:
                    yield {"event": "error", "data": run.error}
                return

            # Wait for new events (20s timeout — SSE ping= keeps connection alive)
            try:
                await asyncio.wait_for(run._new_event.wait(), timeout=20.0)
                run._new_event.clear()
            except asyncio.TimeoutError:
                pass  # no new events yet; loop back and check again

    return EventSourceResponse(
        event_generator(),
        ping=20,
        ping_message_factory=lambda: ServerSentEvent(comment="keep-alive"),
        send_timeout=600,
    )


@app.get("/")
async def health():
    return {"status": "ok", "service": "Stock Intelligence API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)