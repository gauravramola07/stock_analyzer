from crewai import Agent
from tools import fetch_stock_data, fetch_stock_history, fetch_stock_news, search_tool

def create_agents(llm):
    # Using the native LLM object passed from crew.py
    data_researcher = Agent(
        role='Market Data Researcher',
        goal='Fetch accurate financial data for {ticker}',
        backstory="Expert at financial metrics extraction.",
        tools=[fetch_stock_data, fetch_stock_history],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    news_researcher = Agent(
        role='Financial News Analyst',
        goal='Collect the latest news for {ticker}',
        backstory="Seasoned financial journalist scanning sources.",
        tools=[fetch_stock_news, search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    data_analyst = Agent(
        role='Technical Analyst',
        goal='Analyze price trends for {ticker}',
        backstory="Specialist in technical analysis and price action.",
        tools=[fetch_stock_history],
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    financial_expert = Agent(
        role='Senior Equity Analyst',
        goal='Provide a professional investment verdict for {ticker}',
        backstory="Conservative investment advisor.",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    orchestrator = Agent(
        role='Chief Investment Officer',
        goal='Format the final analysis into a valid JSON object',
        backstory="Final quality gatekeeper for JSON formatting.",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )

    return data_researcher, news_researcher, data_analyst, financial_expert, orchestrator
