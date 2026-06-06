import json
import re
from models import (
    FinalVerdict, KeyMetrics, TechnicalAnalysis,
    NewsArticle, TargetPricePoint, TargetPrices,
    CompanyProfile, FinancialRecord,
)


def _extract_json(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()

    for pattern in [r'```json\s*(.*?)\s*```', r'```\s*(.*?)\s*```']:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    break

    return {}


def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _format_market_cap(val) -> str:
    if val is None:
        return "N/A"
    try:
        num = float(val)
        if num >= 1e12:
            return f"${num/1e12:.2f}T"
        elif num >= 1e9:
            return f"${num/1e9:.2f}B"
        elif num >= 1e6:
            return f"${num/1e6:.2f}M"
        else:
            return f"${num:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def assemble_final_result(ticker: str, pre_fetched: dict, agent_outputs: dict) -> str:
    stock_data = pre_fetched.get("stock_data", {})
    news_raw = pre_fetched.get("news", [])
    financial_data = pre_fetched.get("financial_data", {})

    data_json = _extract_json(agent_outputs.get("data", ""))
    news_json = _extract_json(agent_outputs.get("news", ""))
    analysis_json = _extract_json(agent_outputs.get("analysis", ""))
    risk_json = _extract_json(agent_outputs.get("risk", ""))
    expert_json = _extract_json(agent_outputs.get("expert", ""))

    company_name = stock_data.get("shortName") or data_json.get("company_name") or ticker
    current_price = _safe_float(stock_data.get("currentPrice") or data_json.get("current_price"))
    day_change_pct = _safe_float(stock_data.get("dayChangePct") or data_json.get("day_change_pct"))

    key_metrics_data = data_json.get("key_metrics", {})
    key_metrics = KeyMetrics(
        market_cap=_format_market_cap(stock_data.get("marketCap")) or key_metrics_data.get("market_cap"),
        pe_ratio=_safe_float(stock_data.get("trailingPE") or key_metrics_data.get("pe_ratio")),
        beta=_safe_float(stock_data.get("beta") or key_metrics_data.get("beta")),
        dividend_yield=_safe_float(stock_data.get("dividendYield") or key_metrics_data.get("dividend_yield")),
        fifty_two_week_high=_safe_float(stock_data.get("fiftyTwoWeekHigh") or key_metrics_data.get("fifty_two_week_high")),
        fifty_two_week_low=_safe_float(stock_data.get("fiftyTwoWeekLow") or key_metrics_data.get("fifty_two_week_low")),
        volume=stock_data.get("volume") or key_metrics_data.get("volume"),
    )

    company_profile = CompanyProfile(
        business_summary=stock_data.get("longBusinessSummary", ""),
        sector=stock_data.get("sector", ""),
        industry=stock_data.get("industry", ""),
        full_time_employees=stock_data.get("fullTimeEmployees"),
        country=stock_data.get("country", ""),
        city=stock_data.get("city", ""),
        website=stock_data.get("website", ""),
    )

    financial_records_raw = financial_data.get("records", [])
    financial_records = [
        FinancialRecord(
            period=r.get("period", ""),
            revenue=r.get("revenue"),
            net_income=r.get("net_income"),
            gross_profit=r.get("gross_profit"),
            total_assets=r.get("total_assets"),
            total_debt=r.get("total_debt"),
            operating_cash_flow=r.get("operating_cash_flow"),
            source=r.get("source", "SEC EDGAR / yfinance"),
        )
        for r in financial_records_raw
    ]

    news_articles_raw = news_json.get("news_summary", [])
    if news_articles_raw and isinstance(news_articles_raw, list) and len(news_articles_raw) > 0:
        final_news = []
        for a in news_articles_raw[:5]:
            if isinstance(a, dict):
                final_news.append(NewsArticle(
                    title=str(a.get("title", "") or ""),
                    source=str(a.get("source", "") or ""),
                    date=str(a.get("date", "") or ""),
                    sentiment=str(a.get("sentiment", "Neutral") or "Neutral"),
                    summary=str(a.get("summary", "") or ""),
                    url=a.get("url"),
                ))
        if not final_news and news_raw:
            final_news = [
                NewsArticle(
                    title=str(a.get("title", "") or "Untitled"),
                    source=str(a.get("source", "") or ""),
                    date=str(a.get("date", "") or ""),
                    sentiment=str(a.get("sentiment", "Neutral") or "Neutral"),
                    summary=str(a.get("summary", "") or a.get("title", "") or "No summary available."),
                    url=a.get("url"),
                )
                for a in news_raw[:5]
            ]
    elif news_raw:
        final_news = [
            NewsArticle(
                title=str(a.get("title", "") or "Untitled"),
                source=str(a.get("source", "") or ""),
                date=str(a.get("date", "") or ""),
                sentiment=str(a.get("sentiment", "Neutral") or "Neutral"),
                summary=str(a.get("summary", "") or a.get("title", "") or "No summary available."),
                url=a.get("url"),
            )
            for a in news_raw[:5]
        ]
    else:
        final_news = []

    technical_analysis = TechnicalAnalysis(
        trend=analysis_json.get("trend", "N/A"),
        volatility=_safe_float(analysis_json.get("volatility")),
        support=_safe_float(analysis_json.get("support")) if analysis_json.get("support") else None,
        resistance=_safe_float(analysis_json.get("resistance")) if analysis_json.get("resistance") else None,
    )

    volatility = technical_analysis.volatility

    risk_level = risk_json.get("risk_level", "Medium")
    key_risks = risk_json.get("key_risks", [])

    recommendation = expert_json.get("recommendation", "Hold")
    target_price = _safe_float(expert_json.get("target_price"))

    tp_data = expert_json.get("target_prices", {})
    target_prices = TargetPrices(
        three_months=TargetPricePoint(
            price=_safe_float(tp_data.get("three_months", {}).get("price")),
            rationale=tp_data.get("three_months", {}).get("rationale"),
        ) if tp_data.get("three_months") else None,
        six_months=TargetPricePoint(
            price=_safe_float(tp_data.get("six_months", {}).get("price")),
            rationale=tp_data.get("six_months", {}).get("rationale"),
        ) if tp_data.get("six_months") else None,
        twelve_months=TargetPricePoint(
            price=_safe_float(tp_data.get("twelve_months", {}).get("price")),
            rationale=tp_data.get("twelve_months", {}).get("rationale"),
        ) if tp_data.get("twelve_months") else None,
    )

    time_horizon = expert_json.get("time_horizon", "Medium-term")
    confidence_score = _safe_float(expert_json.get("confidence_score"), default=0.5)
    verdict = expert_json.get("verdict", "") or risk_json.get("risk_summary", "") or "No verdict provided."
    quantitative_summary = expert_json.get("quantitative_summary")
    reasoning = expert_json.get("reasoning", [])
    if key_risks:
        reasoning.extend([f"Risk: {r}" for r in key_risks[:3]])

    fundamental_notes = data_json.get("fundamental_notes", "")
    fundamental_analysis = data_json.get("fundamental_analysis", {})
    if not fundamental_analysis and fundamental_notes:
        fundamental_analysis = {"notes": fundamental_notes}

    final = FinalVerdict(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        day_change_pct=day_change_pct,
        volatility=volatility,
        key_metrics=key_metrics,
        company_profile=company_profile,
        financial_records=financial_records,
        news_summary=final_news,
        technical_analysis=technical_analysis,
        fundamental_analysis=fundamental_analysis,
        recommendation=recommendation,
        target_price=target_price,
        target_prices=target_prices,
        time_horizon=time_horizon,
        confidence_score=confidence_score,
        risk_level=risk_level,
        verdict=verdict,
        quantitative_summary=quantitative_summary,
        reasoning=reasoning,
    )

    final_dict = final.model_dump() if hasattr(final, "model_dump") else final.dict()
    return json.dumps(final_dict, indent=2)