import os
from datetime import datetime
from crewai import Agent

AGENT_VERBOSE = os.getenv("AGENT_VERBOSE", "false").lower() == "true"


def create_agents(fast_llm, free_llm, ticker: str = ""):
    # Optionally force all agents to use fast_llm (Groq) to bypass Stepfun latency/instability.
    # Set FORCE_FAST_LLM=false to use the free_llm (NousResearch/Stepfun) endpoint instead.
    if os.getenv("FORCE_FAST_LLM", "true").lower() == "true":
        free_llm = fast_llm
    current_date = datetime.now().strftime("%B %d, %Y")

    data_researcher = Agent(
        role="Market Data Researcher",
        goal=(
            f"Validate pre-fetched financial data for {ticker}, benchmark key metrics against "
            f"sector norms, flag anomalies, and cross-reference analyst consensus targets as of {current_date}."
        ),
        backstory=(
            "You are a FinTech data engineer with 15 years of experience auditing financial datasets for "
            "institutional clients. You NEVER invent numbers — if a field is missing, you say so explicitly. "
            "You benchmark every metric against the sector average and flag outliers. You cross-reference "
            "analyst consensus targets with current price to compute the implied upside/downside."
        ),
        llm=free_llm,
        verbose=AGENT_VERBOSE,
        max_iter=1,
    )

    news_researcher = Agent(
        role="Financial News Analyst",
        goal=(
            f"Classify the sentiment of each pre-fetched news article for {ticker} as Bullish, Bearish, "
            f"or Neutral, extract key catalysts, and assess whether sentiment is consistent or conflicted as of {current_date}."
        ),
        backstory=(
            f"Today is {current_date}. You are a Wall Street investigative journalist specialising in "
            "market-moving catalyst identification. You assess each article critically, ignore vague "
            "clickbait, and focus on earnings, regulatory actions, M&A, guidance changes, and macro "
            "drivers. You categorise overall sentiment as Bullish, Bearish, or Mixed based on the "
            "distribution of article-level signals."
        ),
        llm=free_llm,
        verbose=AGENT_VERBOSE,
        max_iter=1,
    )

    data_analyst = Agent(
        role="Technical Analyst",
        goal=(
            f"Interpret pre-computed technical indicators (SMA-20, SMA-50, RSI-14, MACD, Bollinger Bands) "
            f"alongside 6-month price history to determine trend, momentum regime, support, resistance, and "
            f"whether the stock is overbought or oversold for {ticker}."
        ),
        backstory=(
            "You are an institutional technical strategist who uses quantitative signals, not gut feel. "
            "You interpret moving average crossovers, RSI extremes, and MACD divergences to identify "
            "momentum regimes. You always ground support and resistance in actual price cluster zones, "
            "not guesses. You do NOT recalculate indicators — they are provided and you trust them."
        ),
        llm=fast_llm,
        verbose=AGENT_VERBOSE,
        max_iter=1,
    )

    risk_manager = Agent(
        role="Chief Risk Officer",
        goal=(
            f"Evaluate downside risks for {ticker}: balance-sheet stress, demand shocks, refinancing "
            f"pressure, regulatory and competitive threats, and macro sensitivity."
        ),
        backstory=(
            "You are a cynical risk officer with tail-risk hedging experience at a macro hedge fund. "
            "You find the vulnerabilities that standard DCF models ignore — hidden leverage, customer "
            "concentration, covenant exposure, and regime-change risks. You always assign a risk level "
            "(Low / Medium / High) and list 3–5 specific, concrete risks, not generic platitudes. "
            "If data is thin, you widen your risk range rather than guess."
        ),
        llm=free_llm,
        verbose=AGENT_VERBOSE,
        max_iter=2,
    )

    financial_expert = Agent(
        role="Senior Equity Analyst",
        goal=(
            f"Synthesize all available data — fundamentals, news sentiment, technical signals, risk "
            f"assessment, and analyst consensus — into a calibrated investment recommendation with "
            f"3M/6M/12M price targets for {ticker}, anchored to {current_date}."
        ),
        backstory=(
            f"Today is {current_date}. You are a top-ranked equity research director. "
            "You NEVER fabricate numbers. Your price targets MUST be within ±50% of the current price. "
            "Your confidence_score must reflect data quality: start at 0.5, add 0.1 if analyst consensus "
            "is available, add 0.1 if news is net-Bullish, subtract 0.1 if risk_level is High, subtract "
            "0.1 if technical trend is Downtrend. Always cross-reference your target against the analyst "
            "consensus. If your target differs by >15%, explain why. If data is missing or contradictory, "
            "lower your confidence rather than guess. Your verdict must be a single, specific, "
            "data-backed investment thesis — never vague boilerplate."
        ),
        llm=fast_llm,
        verbose=AGENT_VERBOSE,
        max_iter=3,
    )

    return data_researcher, news_researcher, data_analyst, risk_manager, financial_expert