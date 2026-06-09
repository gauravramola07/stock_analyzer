import json
from crewai import Task


def create_phase1_tasks(ticker, pre_fetched, data_researcher, news_researcher, data_analyst):
    stock_data = pre_fetched.get("stock_data", {})
    history = pre_fetched.get("history", [])
    news = pre_fetched.get("news", [])
    analyst_data = pre_fetched.get("analyst_data", {})
    technical_indicators = pre_fetched.get("technical_indicators", {})

    # Bug 5 fix: Detect ETF/Fund instruments and inject a warning prefix
    instrument_note = ""
    if stock_data.get("isETF"):
        instrument_note = (
            "IMPORTANT: This ticker is an ETF/Fund, not an individual company. "
            "The underlying constituents drive performance, not direct earnings. "
            "Do not apply company-level qualitative narratives (e.g., product launches, "
            "executive changes) to this instrument. Focus on fund-level metrics, "
            "holdings composition, and sector exposure instead.\n\n"
        )

    # Compute implied upside for the data_task prompt
    current_price = stock_data.get("currentPrice") or 0
    mean_target = analyst_data.get("mean_target")
    implied_upside_str = ""
    if current_price and mean_target:
        upside_pct = ((mean_target - current_price) / current_price) * 100
        direction = "upside" if upside_pct >= 0 else "downside"
        implied_upside_str = (
            f"\nAnalyst consensus mean target: ${mean_target:.2f} "
            f"({abs(upside_pct):.1f}% implied {direction} from current price of ${current_price:.2f}). "
            f"Num analysts: {analyst_data.get('num_analysts', 'N/A')}. "
            f"Consensus label: {analyst_data.get('recommendation_key', 'N/A')}."
        )

    # Pre-compute exact 52-week percentage distances to prevent LLM math hallucinations
    fifty_two_week_high = stock_data.get("fiftyTwoWeekHigh")
    fifty_two_week_low = stock_data.get("fiftyTwoWeekLow")
    high_diff_pct_str = "N/A"
    if current_price and fifty_two_week_high:
        high_diff_pct = ((fifty_two_week_high - current_price) / fifty_two_week_high) * 100
        high_diff_pct_str = f"{high_diff_pct:.1f}%"
    low_diff_pct_str = "N/A"
    if current_price and fifty_two_week_low:
        low_diff_pct = ((current_price - fifty_two_week_low) / fifty_two_week_low) * 100
        low_diff_pct_str = f"{low_diff_pct:.1f}%"

    data_task = Task(
        description=f"""{instrument_note}Analyze the following pre-fetched financial data for {ticker}. Validate the numbers,
flag anomalies, benchmark key metrics against sector norms, and interpret the analyst consensus context.

IMPORTANT: Use ONLY the data provided below. Do NOT invoke any tools or fetch additional data.
IMPORTANT: Do NOT invent or estimate any numbers that are not present in the data.
NOTE: The `debtToEquity` field from yfinance is expressed as a percentage (e.g., 53.3 means debt is 53.3% of equity, i.e., a ratio of 0.533). A value below 100 indicates total debt is less than total equity. Do NOT interpret this as a multiplier.

IMPORTANT: Use ONLY these exact pre-computed values for any percentage calculations relative to the 52-week range in your output text:
- Current price (${current_price:.2f}) is exactly {high_diff_pct_str} below the 52-week high of ${fifty_two_week_high or 0.00:.2f}.
- Current price (${current_price:.2f}) is exactly {low_diff_pct_str} above the 52-week low of ${fifty_two_week_low or 0.00:.2f}.
Do NOT calculate these percentages yourself, as you will make rounding or arithmetic mistakes.

STOCK DATA:
{json.dumps(stock_data, indent=2)}

ANALYST CONSENSUS:{implied_upside_str if implied_upside_str else " Not available."}
{json.dumps(analyst_data, indent=2)}

Tasks:
1. Check if valuation metrics (like P/E, Price/Book, or EV/EBITDA) are historically elevated or depressed relative to sector averages. Do NOT explain mathematical identities (such as P/E × EPS = Price) in your notes; focus on what the valuation level implies.
2. Flag any metrics that appear anomalous (e.g., PE > 100, negative revenue growth, zero volume).
3. Note if current price is above or below the analyst consensus target and by how much.
4. Comment on growth metrics (revenue_growth, earnings_growth, profit_margins) if available.
5. Produce a concise fundamental_notes string summarising your findings.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"company_name": "...", "current_price": 0.0, "day_change_pct": 0.0, "key_metrics": {{"market_cap": "...", "pe_ratio": 0.0, "beta": 0.0, "dividend_yield": 0.0, "fifty_two_week_high": 0.0, "fifty_two_week_low": 0.0, "volume": 0}}, "fundamental_notes": "Concise assessment of valuation level implications, growth trajectory, and analyst positioning. Avoid identity arithmetic."}}""",
        expected_output="A JSON object with company_name, current_price, day_change_pct, key_metrics, and fundamental_notes.",
        agent=data_researcher,
    )

    news_task = Task(
        description=f"""Classify the sentiment of each news article for {ticker} and identify key market-moving catalysts.

IMPORTANT: Use ONLY the data provided below. Do NOT invoke any tools or fetch additional data.

NEWS ARTICLES (up to 10):
{json.dumps(news, indent=2)}

Tasks:
1. For each article: assign sentiment (Bullish / Bearish / Neutral) with a one-sentence rationale.
2. Identify the top 3 catalysts most likely to move the stock price.
3. Assess the overall sentiment balance: is the news flow net-Bullish, net-Bearish, or Mixed?
4. Flag any articles about earnings, guidance changes, M&A, regulation, or major product launches — these carry more weight.

Rules:
- If an article is vague or clickbait with no substance, mark it Neutral.
- Do NOT assign Bullish if the headline is positive but the content reveals concerns.
- Overall news sentiment (`overall_sentiment`) must be calculated strictly: it is "Bullish" if bullish articles outnumber bearish articles and represent a significant portion of the news; "Bearish" if bearish outnumber bullish; "Mixed" if there is an active conflict of bullish and bearish signals; and "Neutral" if the majority of articles are Neutral.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"news_summary": [{{"title": "...", "source": "...", "date": "...", "sentiment": "Bullish/Bearish/Neutral", "summary": "...", "url": "..."}}], "key_catalysts": ["catalyst 1", "catalyst 2", "catalyst 3"], "overall_sentiment": "Bullish/Bearish/Mixed/Neutral"}}""",
        expected_output="A JSON object with news_summary (sentiment-classified articles), key_catalysts, and overall_sentiment.",
        agent=news_researcher,
    )

    # Format indicator summary for the analysis prompt
    ti = technical_indicators
    indicators_summary = f"""
Pre-computed Technical Indicators (DO NOT recalculate — use these values directly):
- SMA-20: {ti.get('sma_20', 'N/A')} | Price vs SMA-20: {ti.get('price_vs_sma20', 'N/A')}
- SMA-50: {ti.get('sma_50', 'N/A')} | Price vs SMA-50: {ti.get('price_vs_sma50', 'N/A')}
- RSI-14: {ti.get('rsi_14', 'N/A')} → Signal: {ti.get('rsi_signal', 'N/A')}
- MACD Line: {ti.get('macd_line', 'N/A')} | Signal: {ti.get('macd_signal', 'N/A')} | Histogram: {ti.get('macd_histogram', 'N/A')}
- MACD Crossover: {ti.get('macd_crossover', 'N/A')}
- Bollinger Upper: {ti.get('bb_upper', 'N/A')} | Lower: {ti.get('bb_lower', 'N/A')} | Position (0=low, 1=high): {ti.get('bb_position', 'N/A')}
- 52-week Position (0=at low, 1=at high): {ti.get('fifty_two_week_position', 'N/A')}
- Volume vs 20d Avg: {ti.get('avg_volume_ratio', 'N/A')}x
- 30-day Volatility (annualized): {ti.get('volatility_30d', 'N/A')}
"""

    analysis_task = Task(
        description=f"""Analyze the 6-month price history and pre-computed technical indicators for {ticker}.
Determine trend regime, momentum, support, resistance, and overbought/oversold condition.

IMPORTANT: Use ONLY the data provided below. Do NOT invoke any tools or recalculate indicators.
IMPORTANT: Support and resistance MUST be actual price levels visible in the history data, not guesses.
IMPORTANT: If technical_indicators below is empty, None, or shows "N/A" for all fields, you MUST state explicitly:
  - Set momentum to "Unknown"
  - Set trend to "Insufficient Data"
  - Set rsi_interpretation to "N/A"
  - Set macd_interpretation to "N/A"
  Do NOT infer momentum direction from price history alone when indicators are absent.

{indicators_summary}

PRICE HISTORY (last 6 months, most recent last):
{json.dumps(history[-60:] if len(history) > 60 else history, indent=2)}

Tasks:
1. Determine trend: Classify as one of:
   - "Strong Uptrend" (price is above both SMA-20 and SMA-50, AND momentum is strong as indicated by a bullish MACD crossover or RSI positive momentum).
   - "Moderately Bullish" (price is above SMA-50 but below SMA-20 (minor pullback), OR price is above both SMA-20 and SMA-50 but momentum indicators like RSI and MACD are neutral/weak, or price is near key resistance/52-week high).
   - "Sideways / Consolidation" (price ranging/flat or moving average boundaries converging).
   - "Moderately Bearish" (price is below SMA-50 but above SMA-20, OR price is below both but with neutral/oversold momentum).
   - "Strong Downtrend" (price is below both SMA-20 and SMA-50 with active bearish momentum).
2. Identify a support level: a price zone where the stock repeatedly bounced in the history.
3. Identify a resistance level: a price zone where the stock repeatedly stalled or reversed.
4. Assess momentum: consider RSI ({ti.get('rsi_14', 'N/A')}), MACD histogram trend,
AND the Bollinger Band position ({ti.get('bb_position', 'N/A')} — below 0.20 means price is
near the lower band, a weakness signal; above 0.80 means near upper band, a strength signal).
A position below 0.20 with neutral RSI should NOT be labeled 'Strong' momentum.
5. Interpret MACD: is momentum accelerating (positive histogram growing) or decelerating?
6. Volatility is pre-computed for you as `30-day Volatility (annualized)`. Read this value and output it directly in the `volatility` field as a float.

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"trend": "Strong Uptrend/Moderately Bullish/Sideways / Consolidation/Moderately Bearish/Strong Downtrend", "volatility": 0.0, "support": 0.0, "resistance": 0.0, "momentum": "Strong/Moderate/Weak", "rsi_interpretation": "Overbought/Neutral/Oversold", "macd_interpretation": "Accelerating/Decelerating/Flat"}}""",
        expected_output="A JSON object with trend, volatility, support, resistance, momentum, rsi_interpretation, macd_interpretation.",
        agent=data_analyst,
    )

    return [data_task, news_task, analysis_task]


def create_risk_task(ticker, pre_fetched, phase1_outputs, risk_manager):
    """Create just the risk assessment task for Phase 2 step 1."""
    stock_data = pre_fetched.get("stock_data", {})

    # ETF instrument note
    instrument_note = ""
    if stock_data.get("isETF"):
        instrument_note = (
            "IMPORTANT: This ticker is an ETF/Fund, not an individual company. "
            "The underlying constituents drive performance, not direct earnings. "
            "Do not apply company-level qualitative narratives to this instrument.\n\n"
        )

    risk_task = Task(
        description=f"""{instrument_note}Evaluate downside risks for {ticker} based on the following data and analysis.

IMPORTANT: Use ONLY the data provided. Do NOT invoke any tools.
IMPORTANT: Identify specific, concrete risks — not generic boilerplate. Each risk must reference the data.

STOCK DATA:
{json.dumps(stock_data, indent=2)}

FUNDAMENTAL ASSESSMENT:
{phase1_outputs.get("data", "No data available")}

NEWS ANALYSIS:
{phase1_outputs.get("news", "No news available")}

TECHNICAL ANALYSIS:
{phase1_outputs.get("analysis", "No analysis available")}

Assess specifically:
1. Balance-sheet stress: Is debt-to-equity elevated? Is current ratio low? (Note: The debtToEquity field is a percentage, e.g. 53.3 means 53.3%% of equity = 0.533 ratio. Do NOT overstate risk or flag debt-to-equity as a stress factor or vulnerability if it is below 100 (i.e., total debt < total equity), or if it is in line with/below sector averages, or if the company has massive operating cash flows to cover it. A debt-to-equity ratio below 100%% for a cash-rich, highly profitable blue-chip company is healthy and should not be characterized as a stress or high-leverage risk).
2. Earnings quality: Are profit margins compressing? Is free cash flow weak?
3. Demand risks: What macro or sector headwinds could reduce revenue?
4. Technical risk: Is price near resistance with bearish momentum signals?
5. News-driven risk: Are there regulatory, legal, or competitive threats in the news? (Note: Do NOT overfit to or elevate minor news items—such as satellite partner updates, minor client trials, or launch rumors—into major operational or financial risks unless they are explicitly described as material to earnings. Focus on standard structural risks if news is thin or neutral).

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"risk_level": "Low/Medium/High", "key_risks": ["specific risk 1 with data reference", "specific risk 2", "specific risk 3"], "risk_summary": "Concise 2-3 sentence narrative explaining the dominant risk theme."}}""",
        expected_output="A JSON object with risk_level, key_risks (specific and data-referenced), and risk_summary.",
        agent=risk_manager,
    )

    return risk_task


def create_expert_task(ticker, pre_fetched, phase1_outputs, risk_output, financial_expert):
    """Create the expert synthesis task for Phase 2 step 2.
    
    risk_output is the raw string output from the risk task,
    injected directly into the prompt instead of relying on CrewAI context=[].
    """
    stock_data = pre_fetched.get("stock_data", {})
    analyst_data = pre_fetched.get("analyst_data", {})
    technical_indicators = pre_fetched.get("technical_indicators", {})

    # ETF instrument note
    instrument_note = ""
    if stock_data.get("isETF"):
        instrument_note = (
            "IMPORTANT: This ticker is an ETF/Fund, not an individual company. "
            "The underlying constituents drive performance, not direct earnings. "
            "Do not apply company-level qualitative narratives to this instrument.\n\n"
        )

    current_price = stock_data.get("currentPrice") or 0
    mean_target = analyst_data.get("mean_target")
    high_target = analyst_data.get("high_target")
    low_target = analyst_data.get("low_target")
    num_analysts = analyst_data.get("num_analysts")
    rec_key = analyst_data.get("recommendation_key", "N/A")

    high_target_str = f"${high_target:.2f}" if high_target else "N/A"
    low_target_str = f"${low_target:.2f}" if low_target else "N/A"

    analyst_context = ""
    if mean_target and current_price:
        pct_diff = ((mean_target - current_price) / current_price) * 100
        analyst_context = (
            f"\nWall Street Analyst Consensus ({num_analysts or 'unknown'} analysts):\n"
            f"  Mean target: ${mean_target:.2f} ({pct_diff:+.1f}% vs current ${current_price:.2f})\n"
            f"  High target: {high_target_str}\n"
            f"  Low target: {low_target_str}\n"
            f"  Consensus label: {rec_key}\n"
        )

    consensus_mismatch_instruction = ""
    if rec_key and mean_target and current_price:
        implied_upside = ((mean_target - current_price) / current_price) * 100
        if "buy" in rec_key.lower() and implied_upside < 0:
            consensus_mismatch_instruction = (
                f"\nIMPORTANT VALUATION MISMATCH:\n"
                f"  Wall Street analyst consensus is '{rec_key}', but their mean price target (${mean_target:.2f}) "
                f"is BELOW the current price of ${current_price:.2f}, implying a {abs(implied_upside):.1f}% downside. "
                f"This occurs because the stock has surged rapidly, and analyst price targets are lagging. "
                f"You MUST call out this mismatch explicitly in your 'verdict' and 'reasoning' (e.g., explain that the "
                f"consensus buy recommendation is outdated/lagging behind the rapid price run-up, justifying a Hold/Avoid verdict)."
            )
        elif ("sell" in rec_key.lower() or "underperform" in rec_key.lower()) and implied_upside > 0:
            consensus_mismatch_instruction = (
                f"\nIMPORTANT VALUATION MISMATCH:\n"
                f"  Wall Street analyst consensus is '{rec_key}', but their mean price target (${mean_target:.2f}) "
                f"is ABOVE the current price of ${current_price:.2f}, implying a {implied_upside:.1f}% upside. "
                f"You MUST call out this mismatch explicitly in your 'verdict' and 'reasoning'."
            )

    # Prepare concrete dynamic example of confidence score calculation
    score_example = 0.50
    breakdown_example = "0.50 (baseline)"
    if mean_target:
        score_example += 0.10
        breakdown_example += " + 0.10 (analyst consensus available)"
    # Assume mixed news (no change) and High Risk (-0.10) for illustrative example
    score_example -= 0.10
    breakdown_example += " - 0.10 (High risk_level)"
    pct_diff = abs(((mean_target - current_price) / current_price) * 100) if mean_target and current_price else 0
    example_final_str = f"Confidence score breakdown: {breakdown_example} = {score_example:.2f}. Analyst consensus vs our target: {pct_diff:.1f}% difference." if mean_target else "Confidence score breakdown: 0.50 (baseline) = 0.50."

    expert_task = Task(
        description=f"""{instrument_note}Synthesize all analysis into a calibrated investment recommendation for {ticker}.
 
IMPORTANT: Use ONLY the data provided. Do NOT invoke any tools.
IMPORTANT RULES FOR PRICE TARGETS:
  - target_price MUST be a positive float within ±50% of the current price (${current_price:.2f}).
  - Valid range: ${current_price * 0.5:.2f} to ${current_price * 1.5:.2f}.
  - If your target differs from analyst consensus mean by >15%, explain the deviation in reasoning.
  - Never set target_price to 0.0.
  - Distinct Trajectories: Your 3-month, 6-month, and 12-month target prices MUST show a trajectory reflecting your recommendation and technical/fundamental trend. 
    - For Strong Buy / Buy / Speculative Buy / Accumulate: show sequential appreciation.
    - For Avoid: show sequential depreciation.
    - For Hold: show stable prices near support/resistance or the analyst target, but explain the expected path. Do not just copy the current price across all horizons unless you genuinely predict zero price movement.

IMPORTANT RULES FOR CONFIDENCE SCORE (must follow this formula):
  - Start at 0.50 (baseline)
  - +0.10 if analyst consensus data is available
  - +0.10 if overall news sentiment is net-Bullish
  - -0.10 if risk_level is High
  - -0.10 if technical trend is Strong Downtrend or Moderately Bearish
  - +0.05 if price is near strong support level
  - Clamp final score to [0.20, 0.90]
  - Report your score AND the calculation breakdown in quantitative_summary.

IMPORTANT RULES FOR WRITING JSON OUTPUT:
  - Do NOT copy the raw template strings or placeholders (like "baseline 0.50 ± adjustments = final" or "X%") literally into your JSON fields. You MUST calculate and print the actual math and values.
  - time_horizon MUST be exactly one of: "Short-term", "Medium-term", or "Long-term". Do NOT output all three separated by slashes — choose the single one that best fits the recommendation horizon.
  - Risk-Reward Alignment: If the risk_level is "High" and your recommendation is "Strong Buy", "Buy", or "Speculative Buy", you MUST explicitly justify in your reasoning and verdict why the growth or valuation upside outweighs these significant downside risks (such as high leverage, high beta, or cash flow stress).
  - Fact-Grounding: Every single word and claim in your reasoning, verdict, and rationales must be strictly and directly supported by the provided news articles list and stock data. Do NOT extrapolate, speculate, or introduce any outside knowledge, future events, rumors, or speculation (such as CEO transitions, executive changes, layoffs, or new product launches) that is not explicitly written in the provided text. If a fact is not in the text, it is completely non-existent to you.
  - Toned-Down Recommendations: If the overall news sentiment is Neutral or Mixed, and there is a lack of fresh, material event-driven positive catalysts in the news feed, do NOT recommend a 'Strong Buy'. In these situations, limit your rating to a more balanced 'Buy', 'Accumulate' (Moderate Buy), or 'Hold' based on valuation and fundamentals.
  {consensus_mismatch_instruction}

CURRENT STOCK PRICE: ${current_price:.2f}
{analyst_context if analyst_context else "Analyst consensus: Not available."}

RSI: {technical_indicators.get('rsi_14', 'N/A')} ({technical_indicators.get('rsi_signal', 'N/A')})
MACD Crossover: {technical_indicators.get('macd_crossover', 'N/A')}
Price vs SMA-50: {technical_indicators.get('price_vs_sma50', 'N/A')}

FUNDAMENTAL ASSESSMENT:
{phase1_outputs.get("data", "No data available")}

NEWS ANALYSIS:
{phase1_outputs.get("news", "No news available")}

TECHNICAL ANALYSIS:
{phase1_outputs.get("analysis", "No analysis available")}

RISK ASSESSMENT (from Chief Risk Officer):
{risk_output}

Output ONLY a JSON object (no markdown fences, no extra text) with this exact structure:
{{"recommendation": "Strong Buy/Buy/Speculative Buy/Accumulate/Hold/Avoid", "target_price": 0.0, "target_prices": {{"three_months": {{"price": 0.0, "rationale": "..."}}, "six_months": {{"price": 0.0, "rationale": "..."}}, "twelve_months": {{"price": 0.0, "rationale": "..."}}}}, "time_horizon": "MUST be exactly one of: Short-term, Medium-term, or Long-term", "confidence_score": 0.5, "verdict": "Specific 1-2 sentence investment thesis grounded in data.", "quantitative_summary": "{example_final_str}", "reasoning": ["data-backed point 1", "data-backed point 2", "data-backed point 3"]}}""",
        expected_output="A JSON object with recommendation, target_prices, confidence_score, verdict, quantitative_summary, and reasoning.",
        agent=financial_expert,
        context=[],  # Risk output is directly injected above, no context dependency
    )

    return expert_task