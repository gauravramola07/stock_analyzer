from crewai import Task

def create_tasks(ticker, data_researcher, news_researcher, data_analyst, financial_expert, orchestrator):
    data_task = Task(
        description=f"Fetch the latest price, market cap, PE ratio, and 52-week range for {ticker}.",
        expected_output="A structured summary of key financial metrics.",
        agent=data_researcher
    )

    news_task = Task(
        description=f"Gather the last 10 news articles for {ticker}. Summarize the sentiment of each.",
        expected_output="A list of recent news articles with titles, sentiment, and short summaries.",
        agent=news_researcher
    )

    analysis_task = Task(
        description=f"Analyze the 30-day price history of {ticker}. Calculate trend direction and volatility.",
        expected_output="A technical analysis report with volatility scores and trend assessment.",
        agent=data_analyst
    )

    expert_task = Task(
        description=f"Using the data, news, and technical analysis, provide a target price and recommendation for {ticker}.",
        expected_output="A professional investment recommendation with target price and time horizon.",
        agent=financial_expert,
        context=[data_task, news_task, analysis_task]
    )

    orchestration_task = Task(
        description=f"""Combine all previous findings into a single, clean JSON object for {ticker}.
        
        CRITICAL: You MUST include the top 5 news articles from the News Researcher in the 'news_summary' list. 
        Each news item must have title, source, date, sentiment, and summary. Do not leave 'news_summary' as an empty list.

        The final output must be ONLY the raw JSON. Do not include markdown formatting tags.
        Required JSON Structure:
        {{
            "ticker": "{ticker}",
            "company_name": "...",
            "current_price": 0.0,
            "day_change_pct": 0.0,
            "volatility": 0.0,
            "key_metrics": {{ "market_cap": "...", "pe_ratio": 0.0, "beta": 0.0 }},
            "news_summary": [{{ "title": "...", "source": "...", "date": "...", "sentiment": "...", "summary": "..." }}],
            "technical_analysis": {{ "trend": "...", "volatility": 0.0 }},
            "fundamental_analysis": {{}},
            "recommendation": "Buy/Hold/Avoid",
            "target_price": 0.0,
            "time_horizon": "...",
            "confidence_score": 0.5,
            "risk_level": "Low/Medium/High",
            "verdict": "...",
            "reasoning": ["point 1", "point 2"]
        }}
        """,
        expected_output="A perfectly formatted JSON object including the news articles.",
        agent=orchestrator,
        context=[expert_task, news_task]
    )

    return [data_task, news_task, analysis_task, expert_task, orchestration_task]
