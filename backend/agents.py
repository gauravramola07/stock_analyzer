from datetime import datetime
from crewai import Agent


def create_agents(llm):
    current_date = datetime.now().strftime("%B %d, %Y")

    data_researcher = Agent(
        role="Market Data Researcher",
        goal=f"Analyze and validate pre-fetched financial data for {{ticker}}, identifying anomalies and providing fundamental context as of {current_date}.",
        backstory="FinTech data engineer who validates financial datasets and identifies sector-relative valuation context. Flag anomalies and missing data.",
        llm=llm,
        verbose=False,
    )

    news_researcher = Agent(
        role="Financial News Analyst",
        goal=f"Classify sentiment of each pre-fetched news article for {{ticker}} as Bullish, Bearish, or Neutral, and highlight key catalysts up to {current_date}.",
        backstory=f"Wall Street investigative journalist. Today: {current_date}. Classify news sentiment and identify market-moving catalysts. Ignore clickbait.",
        llm=llm,
        verbose=False,
    )

    data_analyst = Agent(
        role="Technical Analyst",
        goal="Analyze the pre-fetched 30-day price history to determine trend, volatility, support, and resistance for {ticker}.",
        backstory="Institutional technical strategist. Identify momentum, mean-reversion, and structural price levels from historical data.",
        llm=llm,
        verbose=False,
    )

    risk_manager = Agent(
        role="Chief Risk Officer",
        goal="Evaluate downside risks, margin pressures, and structural threats for {ticker} based on provided data and analysis.",
        backstory="Cynical risk officer with tail-risk hedging experience. Find vulnerabilities standard models ignore.",
        llm=llm,
        verbose=False,
    )

    financial_expert = Agent(
        role="Senior Equity Analyst",
        goal=f"Synthesize all data into a recommendation with 3M/6M/12M price targets and investment thesis for {{ticker}}, anchored to {current_date}.",
        backstory=f"Top-ranked equity research director. Anchor projections to {current_date}. Data-backed theses, never guesses.",
        llm=llm,
        verbose=False,
    )

    return data_researcher, news_researcher, data_analyst, risk_manager, financial_expert