import json
from crewai import Task


def create_phase1_tasks(ticker, pre_fetched, data_researcher, news_researcher, data_analyst):
    stock_data = pre_fetched.get("stock_data", {})
    history = pre_fetched.get("history", [])
    news = pre_fetched.get("news", [])

    data_task = Task(
        description=f"""Analyze the following pre-fetched financial data for {ticker}. Validate the numbers, identify anomalies, and provide fundamental context.

STOCK DATA:
{json.dumps(stock_data, indent=2)}

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"company_name": "...", "current_price": 0.0, "day_change_pct": 0.0, "key_metrics": {{\"market_cap\": "...", "pe_ratio": 0.0, "beta": 0.0, "dividend_yield": 0.0, "fifty_two_week_high": 0.0, "fifty_two_week_low": 0.0, "volume": 0}}, "fundamental_notes": "Brief assessment"}}""",
        expected_output="A JSON object with company_name, current_price, day_change_pct, key_metrics, and fundamental_notes.",
        agent=data_researcher,
    )

    news_task = Task(
        description=f"""Classify the sentiment of each news article for {ticker} and identify key catalysts.

NEWS ARTICLES:
{json.dumps(news, indent=2)}

For each article, assign sentiment: Bullish, Bearish, or Neutral. Highlight the top 3 catalysts.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"news_summary": [{{\"title\": "...", "source": "...", "date": "...", "sentiment": "Bullish/Bearish/Neutral", "summary": "...", "url": "..."}}], "key_catalysts": ["catalyst 1", "catalyst 2", "catalyst 3"]}}""",
        expected_output="A JSON object with news_summary (sentiment-classified articles) and key_catalysts.",
        agent=news_researcher,
    )

    analysis_task = Task(
        description=f"""Analyze the 30-day price history for {ticker}. Determine trend, volatility, support, and resistance.

PRICE HISTORY:
{json.dumps(history, indent=2)}

Calculate: trend direction (Uptrend/Downtrend/Sideways), volatility, support level, and resistance level.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"trend": "Uptrend/Downtrend/Sideways", "volatility": 0.0, "support": 0.0, "resistance": 0.0}}""",
        expected_output="A JSON object with trend, volatility, support, and resistance.",
        agent=data_analyst,
    )

    return [data_task, news_task, analysis_task]


def create_phase2_tasks(ticker, pre_fetched, phase1_outputs, risk_manager, financial_expert):
    stock_data = pre_fetched.get("stock_data", {})

    risk_task = Task(
        description=f"""Evaluate downside risks for {ticker} based on the following data and analysis.

STOCK DATA:
{json.dumps(stock_data, indent=2)}

FUNDAMENTAL ASSESSMENT:
{phase1_outputs.get("data", "No data available")}

NEWS ANALYSIS:
{phase1_outputs.get("news", "No news available")}

TECHNICAL ANALYSIS:
{phase1_outputs.get("analysis", "No analysis available")}

Assess: balance-sheet risk, demand shocks, refinancing pressure, regulatory risk, and competitive threats.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"risk_level": "Low/Medium/High", "key_risks": ["risk 1", "risk 2", "risk 3"], "risk_summary": "Brief narrative"}}""",
        expected_output="A JSON object with risk_level, key_risks, and risk_summary.",
        agent=risk_manager,
    )

    expert_task = Task(
        description=f"""Synthesize all analysis into a final investment recommendation for {ticker}.

STOCK DATA:
{json.dumps(stock_data, indent=2)}

FUNDAMENTAL ASSESSMENT:
{phase1_outputs.get("data", "No data available")}

NEWS ANALYSIS:
{phase1_outputs.get("news", "No news available")}

TECHNICAL ANALYSIS:
{phase1_outputs.get("analysis", "No analysis available")}

Provide: recommendation, 3M/6M/12M price targets with rationales, confidence score (0-1), time horizon, verdict, and reasoning.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"recommendation": "Buy/Hold/Avoid", "target_price": 0.0, "target_prices": {{\"three_months": {{\"price": 0.0, "rationale": "..."}}, "six_months": {{\"price": 0.0, "rationale": "..."}}, "twelve_months": {{\"price": 0.0, "rationale": "..."}}}}, "time_horizon": "Short-term/Medium-term/Long-term", "confidence_score": 0.5, "verdict": "Concise thesis", "quantitative_summary": "Summary", "reasoning": ["point 1", "point 2"]}}""",
        expected_output="A JSON object with recommendation, target_prices, confidence_score, verdict, and reasoning.",
        agent=financial_expert,
        context=[risk_task],
    )

    return [risk_task, expert_task]