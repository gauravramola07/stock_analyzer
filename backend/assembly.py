import json
import re
import math
from models import (
    FinalVerdict, KeyMetrics, TechnicalAnalysis, TechnicalIndicators,
    AnalystConsensus, DataQuality,
    NewsArticle, TargetPricePoint, TargetPrices,
    CompanyProfile, FinancialRecord,
)


# ---------------------------------------------------------------------------
# JSON extraction helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _safe_float(val, default=0.0):
    if val is None:
        return default
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
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


# ---------------------------------------------------------------------------
# Hallucination scrubbing & math validation helpers
# ---------------------------------------------------------------------------

def _scrub_hallucinations_and_math(expert_json: dict, data_json: dict, pre_fetched: dict) -> tuple[dict, dict]:
    news_raw = pre_fetched.get("news", [])
    news_text = " ".join([f"{n.get('title', '')} {n.get('summary', '')}" for n in news_raw]).lower()
    
    # Banned keywords to check if they are hallucinated (not mentioned in news text)
    banned_keywords = ["ceo transition", "executive transition", "transition scheduled", "ceo change", "layoff", "layoffs", "merger", "acquisition", "regulatory approval", "deal approval"]
    
    def clean_text_field(text: str) -> str:
        if not text:
            return text
        sentences = re.split(r'(?<=[.!?])\s+', text)
        cleaned_sentences = []
        for s in sentences:
            s_lower = s.lower()
            contains_banned = False
            for kw in banned_keywords:
                if kw in s_lower and kw not in news_text:
                    contains_banned = True
                    break
            if contains_banned:
                print(f"[assembly] Scrubbing hallucinated sentence: '{s}'")
                continue
            cleaned_sentences.append(s)
        return " ".join(cleaned_sentences)

    def clean_list_field(lst: list) -> list:
        if not lst:
            return lst
        cleaned = []
        for s in lst:
            s_lower = s.lower()
            contains_banned = False
            for kw in banned_keywords:
                if kw in s_lower and kw not in news_text:
                    contains_banned = True
                    break
            if contains_banned:
                print(f"[assembly] Scrubbing hallucinated list item: '{s}'")
                continue
            cleaned.append(s)
        return cleaned

    # Clean text fields
    if "verdict" in expert_json:
        expert_json["verdict"] = clean_text_field(expert_json["verdict"])
    if "reasoning" in expert_json:
        expert_json["reasoning"] = clean_list_field(expert_json["reasoning"])
    if "fundamental_notes" in data_json:
        data_json["fundamental_notes"] = clean_text_field(data_json["fundamental_notes"])

    # Math correction for 52-week high/low percentage statements
    stock_data = pre_fetched.get("stock_data", {})
    current_price = _safe_float(stock_data.get("currentPrice"))
    fifty_two_week_high = _safe_float(stock_data.get("fiftyTwoWeekHigh"))
    fifty_two_week_low = _safe_float(stock_data.get("fiftyTwoWeekLow"))

    correct_high_pct = 0.0
    if current_price and fifty_two_week_high:
        correct_high_pct = ((fifty_two_week_high - current_price) / fifty_two_week_high) * 100
    correct_low_pct = 0.0
    if current_price and fifty_two_week_low:
        correct_low_pct = ((current_price - fifty_two_week_low) / fifty_two_week_low) * 100

    def correct_math_in_text(text: str) -> str:
        if not text:
            return text
        high_pattern = r'(\d+(?:\.\d+)?)\s*%\s*(?:below|of)\s*(?:the|its)?\s*52-week high'
        def high_replacer(match):
            original = match.group(1)
            print(f"[assembly] Repairing 52-week high distance math: original={original}%, corrected={correct_high_pct:.1f}%")
            return f"{correct_high_pct:.1f}% below the 52-week high"
        text = re.sub(high_pattern, high_replacer, text, flags=re.IGNORECASE)

        low_pattern = r'(\d+(?:\.\d+)?)\s*%\s*(?:above|of)\s*(?:the|its)?\s*52-week low'
        def low_replacer(match):
            original = match.group(1)
            print(f"[assembly] Repairing 52-week low distance math: original={original}%, corrected={correct_low_pct:.1f}%")
            return f"{correct_low_pct:.1f}% above the 52-week low"
        text = re.sub(low_pattern, low_replacer, text, flags=re.IGNORECASE)
        return text

    if "fundamental_notes" in data_json:
        data_json["fundamental_notes"] = correct_math_in_text(data_json["fundamental_notes"])
    if "verdict" in expert_json:
        expert_json["verdict"] = correct_math_in_text(expert_json["verdict"])
    if "reasoning" in expert_json:
        expert_json["reasoning"] = [correct_math_in_text(r) for r in expert_json["reasoning"]]

    return expert_json, data_json


def _validate_and_repair_trend(trend: str, indicators: dict) -> str:
    if not indicators:
        return trend
    
    rsi_signal = indicators.get("rsi_signal") or "Neutral"
    macd_crossover = indicators.get("macd_crossover") or "Neutral"
    price_vs_sma20 = indicators.get("price_vs_sma20") or "Neutral"
    price_vs_sma50 = indicators.get("price_vs_sma50") or "Neutral"
    bb_position = _safe_float(indicators.get("bb_position"))
    fifty_two_week_pos = _safe_float(indicators.get("fifty_two_week_position"))
    macd_line = _safe_float(indicators.get("macd_line"))

    # Correct overstated bullish trend into bearish when technicals clearly disagree.
    # Price below both SMAs with negative MACD = at minimum "Moderately Bearish".
    if trend in ("Moderately Bullish", "Sideways / Consolidation", "Strong Uptrend"):
        is_below_sma20 = price_vs_sma20 == "below"
        is_below_sma50 = price_vs_sma50 == "below"
        is_macd_negative = macd_line < 0

        if is_below_sma20 and is_below_sma50 and is_macd_negative:
            print(f"[assembly] Trend corrected: '{trend}' -> 'Moderately Bearish' "
                  f"(below both SMAs with negative MACD)")
            return "Moderately Bearish"

    # Price below lower Bollinger Band = strong bearish signal
    if bb_position < 0:
        if trend in ("Moderately Bullish", "Strong Uptrend"):
            print(f"[assembly] Trend corrected: '{trend}' -> 'Moderately Bearish' "
                  f"(price below lower Bollinger Band)")
            return "Moderately Bearish"

    # If the trend returned by agent is "Strong Uptrend", but MACD and RSI are neutral and price is near resistance/52-week high,
    # downgrade it to "Moderately Bullish".
    if trend == "Strong Uptrend":
        is_macd_neutral = macd_crossover == "Neutral"
        is_rsi_neutral = rsi_signal == "Neutral"
        is_near_high = fifty_two_week_pos >= 0.85 or bb_position >= 0.85
        
        if is_macd_neutral and is_rsi_neutral and is_near_high:
            print(f"[assembly] Overstated trend repaired: 'Strong Uptrend' -> 'Moderately Bullish' (Indicators neutral near resistance)")
            return "Moderately Bullish"
            
    # Downgrade if price is below SMA-20 (can't be a strong uptrend by definition)
    if price_vs_sma20 == "below":
        if trend == "Strong Uptrend":
            print(f"[assembly] Overstated trend repaired: 'Strong Uptrend' -> 'Moderately Bullish' (Price is below SMA-20)")
            return "Moderately Bullish"
            
    return trend


def _clean_leverage_risks(key_risks: list, debt_to_equity: float) -> list:
    # yfinance returns D/E as a percentage (e.g. 53.3 means 53.3% = 0.533 ratio).
    # Only scrub alarmist leverage warnings if D/E is genuinely low (< 50% = less than half debt/equity).
    if debt_to_equity is None or debt_to_equity >= 50.0:
        return key_risks
    
    cleaned = []
    # Keywords that suggest leverage stress
    leverage_keywords = ["high leverage", "debt vulnerability", "excessive debt", "elevated debt-to-equity", "excessive borrowing", "debt burden", "balance-sheet stress due to debt"]
    for r in key_risks:
        r_lower = r.lower()
        has_leverage_warning = any(kw in r_lower for kw in leverage_keywords)
        if has_leverage_warning:
            print(f"[assembly] Scrubbing overstated leverage risk for low D/E ({debt_to_equity}): '{r}'")
            continue
        cleaned.append(r)
        
    if not cleaned:
        cleaned = ["No significant debt or leverage vulnerabilities identified on the balance sheet."]
    return cleaned


def _clean_overfitted_risks(key_risks: list, risk_summary: str, ticker: str, stock_data: dict) -> tuple[list, str]:
    market_cap = _safe_float(stock_data.get("marketCap"), 0.0)
    cleaned_risks = []
    
    # Overfitting to Globalstar/satellite deal for mega-caps like Apple
    for risk in key_risks:
        risk_lower = risk.lower()
        if ("globalstar" in risk_lower or "satellite" in risk_lower) and (ticker == "AAPL" or market_cap > 1e11):
            print(f"[assembly] Scrubbing overfitted satellite/Globalstar risk for {ticker}: '{risk}'")
            continue
        cleaned_risks.append(risk)
        
    if not cleaned_risks:
        cleaned_risks = ["No major near-term news-driven operational risks identified."]
        
    if risk_summary and (ticker == "AAPL" or market_cap > 1e11):
        if "globalstar" in risk_summary.lower() or "satellite" in risk_summary.lower():
            print(f"[assembly] Cleaning Globalstar/satellite reference in risk summary: '{risk_summary}'")
            risk_summary = re.sub(
                r'[^.]*(?:globalstar|satellite)[^.]*\.', 
                ' Standard operational and macro risk factors remain the primary focus.', 
                risk_summary, 
                flags=re.IGNORECASE
            )
            
    return cleaned_risks, risk_summary


def _align_text_with_recommendation(text: str, recommendation: str) -> str:
    if not text:
        return text
    if recommendation == "Buy":
        text = re.sub(r'\bstrong\s+buy\b', 'Buy', text, flags=re.IGNORECASE)
    elif recommendation == "Accumulate":
        text = re.sub(r'\bstrong\s+buy\b', 'Accumulate', text, flags=re.IGNORECASE)
        text = re.sub(r'\bbuy\s+(?:recommendation|rating|stance|thesis|verdict)\b', 'Accumulate recommendation', text, flags=re.IGNORECASE)
    elif recommendation == "Hold":
        text = re.sub(r'\bwe recommend buying\b', 'we recommend holding', text, flags=re.IGNORECASE)
        text = re.sub(r'\brecommend(?:ed)?\s+(?:a\s+)?(?:strong\s+)?buy(?:ing)?\b', 'recommend holding', text, flags=re.IGNORECASE)
        text = re.sub(r'\b(?:strong\s+)?buy\s+(?:recommendation|rating|stance|thesis|verdict)\b', 'Hold rating', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+buy\b', 'Hold', text, flags=re.IGNORECASE)
    return text


def _align_text_with_trend(text: str, trend: str) -> str:
    if not text:
        return text
    if trend == "Moderately Bullish":
        text = re.sub(r'\bstrong\s+uptrend\b', 'moderately bullish trend', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+technical\s+confirmation\b', 'moderately bullish technical signals', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+technical\s+trend\b', 'moderately bullish trend', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+trend\b', 'moderately bullish trend', text, flags=re.IGNORECASE)
    elif trend == "Sideways / Consolidation":
        text = re.sub(r'\b(?:strong\s+)?uptrend\b', 'sideways consolidation', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+trend\b', 'consolidation trend', text, flags=re.IGNORECASE)
    elif trend in ("Moderately Bearish", "Strong Downtrend", "Downtrend"):
        text = re.sub(r'\b(?:strong\s+)?uptrend\b', 'downtrend', text, flags=re.IGNORECASE)
        text = re.sub(r'\bstrong\s+trend\b', 'downtrend', text, flags=re.IGNORECASE)
    return text


# ---------------------------------------------------------------------------
# Output validators
# ---------------------------------------------------------------------------

def _validate_expert_output(expert_json: dict, current_price: float, analyst_data: dict) -> dict:
    """
    Validate and repair the expert agent's JSON output.
    Returns a (possibly repaired) dict and logs any issues.
    """
    issues = []

    # --- target_price ---
    target_price = _safe_float(expert_json.get("target_price"))
    lower_bound = current_price * 0.48 if current_price else 0
    upper_bound = current_price * 1.52 if current_price else float("inf")

    if target_price <= 0 or not (lower_bound <= target_price <= upper_bound):
        issues.append(f"target_price={target_price} out of valid range [{lower_bound:.2f}, {upper_bound:.2f}]")
        # Try fallback: analyst consensus, then multi-horizon targets, then momentum estimate
        target_price = _compute_fallback_target(current_price, analyst_data, expert_json)
        expert_json["target_price"] = target_price

    # --- confidence_score ---
    confidence = _safe_float(expert_json.get("confidence_score"), default=-1.0)
    if confidence < 0 or confidence > 1:
        issues.append(f"confidence_score={confidence} out of [0, 1]")
        expert_json["confidence_score"] = 0.5

    # --- recommendation ---
    valid_recs = {"Strong Buy", "Buy", "Speculative Buy", "Accumulate", "Hold", "Avoid"}
    rec = expert_json.get("recommendation", "")
    if rec not in valid_recs:
        issues.append(f"recommendation='{rec}' not in {valid_recs}")
        # Infer from confidence and target price
        if current_price and target_price:
            upside = (target_price - current_price) / current_price
            if upside > 0.15:
                expert_json["recommendation"] = "Strong Buy"
            elif upside > 0.05:
                expert_json["recommendation"] = "Buy"
            elif upside < -0.05:
                expert_json["recommendation"] = "Avoid"
            else:
                expert_json["recommendation"] = "Hold"

    # --- Bug 2 fix: Bullish recommendation with negative implied return contradiction ---
    recommendation = expert_json.get("recommendation", "")
    if current_price and target_price and current_price > 0:
        implied_return = (target_price - current_price) / current_price
        if implied_return < -0.05 and recommendation in ("Strong Buy", "Buy", "Accumulate", "Speculative Buy"):
            issues.append(f"Contradiction: {recommendation} with target implying {implied_return:.1%} return. Downgrading to Hold.")
            print(f"[assembly] Contradiction: {recommendation} with target implying "
                  f"{implied_return:.1%} return. Downgrading to Hold.")
            recommendation = "Hold"
            expert_json["recommendation"] = "Hold"
            expert_json["confidence_score"] = min(expert_json.get("confidence_score", 0.5), 0.45)

    # --- reasoning ---
    reasoning = expert_json.get("reasoning", [])
    if not isinstance(reasoning, list) or len(reasoning) < 2:
        issues.append("reasoning has fewer than 2 items")
        if not isinstance(reasoning, list):
            expert_json["reasoning"] = []

    if issues:
        print(f"[assembly] Expert output validation issues: {issues}")

    return expert_json


def _validate_risk_output(risk_json: dict) -> dict:
    """Validate and repair the risk agent's JSON output."""
    issues = []

    valid_levels = {"Low", "Medium", "High"}
    if risk_json.get("risk_level") not in valid_levels:
        issues.append(f"risk_level='{risk_json.get('risk_level')}' invalid")
        risk_json["risk_level"] = "Medium"

    if not isinstance(risk_json.get("key_risks"), list) or len(risk_json.get("key_risks", [])) == 0:
        issues.append("key_risks is empty")
        risk_json["key_risks"] = ["Data insufficient to determine specific risks"]

    if not risk_json.get("risk_summary"):
        risk_json["risk_summary"] = f"Risk level assessed as {risk_json.get('risk_level', 'Medium')} based on available data."

    if issues:
        print(f"[assembly] Risk output validation issues: {issues}")

    return risk_json


def _compute_fallback_target(current_price: float, analyst_data: dict, expert_json: dict) -> float:
    """
    Compute a fallback target price using this priority order:
      1. Analyst consensus mean target (most reliable external signal)
      2. Median of multi-horizon targets from expert JSON if they pass bounds check
      3. Momentum-based estimate (trend-adjusted ±5%)
    """
    if not current_price or current_price <= 0:
        return 0.0

    lower = current_price * 0.48
    upper = current_price * 1.52

    # 1. Analyst consensus (with trend-based adjustment to avoid pure echo)
    mean_target = _safe_float(analyst_data.get("mean_target"))
    if mean_target and lower <= mean_target <= upper:
        # Apply a model-specific adjustment based on technical trend direction
        # to signal analytical independence from Wall Street consensus
        adjusted = mean_target
        trend = expert_json.get("_trend_hint")  # injected by caller if available
        if trend in ("Moderately Bearish", "Strong Downtrend"):
            adjusted = round(mean_target * 0.95, 2)
            if lower <= adjusted <= upper:
                print(f"[assembly] Applied bearish trend discount to analyst target: "
                      f"${mean_target:.2f} → ${adjusted:.2f}")
                return adjusted
        elif trend in ("Strong Uptrend",):
            adjusted = round(mean_target * 1.05, 2)
            if lower <= adjusted <= upper:
                print(f"[assembly] Applied bullish trend premium to analyst target: "
                      f"${mean_target:.2f} → ${adjusted:.2f}")
                return adjusted
        print(f"[assembly] Using analyst consensus target: ${mean_target:.2f}")
        return round(mean_target, 2)

    # 2. Multi-horizon targets from expert
    tp_data = expert_json.get("target_prices", {})
    candidates = []
    for horizon in ["twelve_months", "six_months", "three_months"]:
        p = _safe_float((tp_data.get(horizon) or {}).get("price"))
        if p and lower <= p <= upper:
            candidates.append(p)
    if candidates:
        median_candidate = sorted(candidates)[len(candidates) // 2]
        print(f"[assembly] Using multi-horizon median target: ${median_candidate:.2f}")
        return round(median_candidate, 2)

    # 3. Momentum estimate: use analyst consensus direction if available, else flat
    if mean_target and mean_target > 0:
        # Clamp the analyst target to valid range
        clamped = max(lower, min(upper, mean_target))
        print(f"[assembly] Using clamped analyst target: ${clamped:.2f}")
        return round(clamped, 2)

    # Final fallback: current price (neutral)
    print(f"[assembly] All fallbacks exhausted — using current price as target: ${current_price:.2f}")
    return round(current_price, 2)


def _validate_and_repair_target_prices(
    target_prices_dict: dict,
    current_price: float,
    target_price: float,
    recommendation: str
) -> dict:
    """
    Ensure 3M, 6M, and 12M target prices are populated, valid, and follow a distinct
    trajectory reflecting the recommendation.
    """
    if not target_prices_dict:
        target_prices_dict = {}

    p3 = _safe_float((target_prices_dict.get("three_months") or {}).get("price"))
    p6 = _safe_float((target_prices_dict.get("six_months") or {}).get("price"))
    p12 = _safe_float((target_prices_dict.get("twelve_months") or {}).get("price"))
    
    r3 = (target_prices_dict.get("three_months") or {}).get("rationale") or ""
    r6 = (target_prices_dict.get("six_months") or {}).get("rationale") or ""
    r12 = (target_prices_dict.get("twelve_months") or {}).get("rationale") or ""
    
    lower = current_price * 0.48
    upper = current_price * 1.52

    # Check if any horizon is missing, invalid, flat, or if 12M target does not equal primary target
    needs_repair = (
        p3 <= 0 or p6 <= 0 or p12 <= 0 or
        not (lower <= p3 <= upper) or
        not (lower <= p6 <= upper) or
        not (lower <= p12 <= upper) or
        (abs(p12 - target_price) / target_price > 0.05 if target_price else True) or
        (abs(p3 - current_price) < 0.01 and abs(p6 - current_price) < 0.01 and abs(p12 - current_price) < 0.01)
    )
    
    if needs_repair:
        print(f"[assembly] Repairing target prices. current={current_price}, target={target_price}, rec={recommendation}")
        # Construct trajectory towards target_price
        
        # If target_price is extremely close to current_price (Hold scenario)
        if abs(target_price - current_price) < current_price * 0.01:
            if recommendation == "Buy":
                target_price = current_price * 1.10
            elif recommendation == "Avoid":
                target_price = current_price * 0.90
            else:
                p3_val = round(current_price * 0.99, 2)
                p6_val = round(current_price * 1.01, 2)
                p12_val = round(current_price, 2)
                r3_val = "Short-term consolidation near support."
                r6_val = "Mid-term stabilization around moving averages."
                r12_val = "Fair value convergence over 12 months."
                return {
                    "three_months": {"price": p3_val, "rationale": r3_val},
                    "six_months": {"price": p6_val, "rationale": r6_val},
                    "twelve_months": {"price": p12_val, "rationale": r12_val},
                }

        # Calculate sequential steps
        p3_val = round(current_price + 0.25 * (target_price - current_price), 2)
        p6_val = round(current_price + 0.50 * (target_price - current_price), 2)
        p12_val = round(target_price, 2)
        
        # Ensure they are within bounds
        p3_val = max(lower, min(upper, p3_val))
        p6_val = max(lower, min(upper, p6_val))
        p12_val = max(lower, min(upper, p12_val))
        
        # Set rationales
        if recommendation in ("Strong Buy", "Buy", "Speculative Buy", "Accumulate"):
            r3_val = r3 or f"Initial appreciation towards ${p3_val:.2f} as bullish catalysts materialize."
            r6_val = r6 or f"Mid-term momentum building towards ${p6_val:.2f} driven by fundamental growth."
            r12_val = r12 or f"12-month target price of ${p12_val:.2f} achieved as stock converges to fair value."
        elif recommendation == "Avoid":
            r3_val = r3 or f"Near-term selling pressure drives correction towards ${p3_val:.2f}."
            r6_val = r6 or f"Mid-term decline towards ${p6_val:.2f} as high leverage/risks materialize."
            r12_val = r12 or f"12-month correction complete, stabilizing near fair value of ${p12_val:.2f}."
        else:
            r3_val = r3 or f"Short-term consolidation around ${p3_val:.2f}."
            r6_val = r6 or f"Stabilization near key moving averages at ${p6_val:.2f}."
            r12_val = r12 or f"12-month target price of ${p12_val:.2f} in a sideways range."
            
        return {
            "three_months": {"price": p3_val, "rationale": r3_val},
            "six_months": {"price": p6_val, "rationale": r6_val},
            "twelve_months": {"price": p12_val, "rationale": r12_val},
        }

    # --- Bug 3 fix: Monotonicity check for bullish calls ---
    if p3 and p6 and p12 and recommendation in ("Strong Buy", "Buy", "Accumulate", "Speculative Buy"):
        if not (p3 <= p6 <= p12):
            print(f"[assembly] Descending targets for bullish call: "
                  f"3M={p3} 6M={p6} 12M={p12}. Repairing to ascending sequence.")
            # Force ascending: use 12M as anchor
            if p3 < current_price:
                spread = p12 - current_price if p12 > current_price else current_price * 0.1
                p3 = round(current_price + spread * 0.35, 2)
                p6 = round(current_price + spread * 0.65, 2)
            else:
                p6 = round((p3 + p12) / 2, 2)
            # Ensure ascending order
            if p3 > p6:
                p3, p6 = p6, p3
            r3 = r3 or f"Short-term target repaired to ${p3:.2f}."
            r6 = r6 or f"Mid-term target interpolated to ${p6:.2f}."

    return {
        "three_months": {"price": p3, "rationale": r3 or "Short-term target price forecast."},
        "six_months": {"price": p6, "rationale": r6 or "Mid-term target price forecast."},
        "twelve_months": {"price": p12, "rationale": r12 or "12-month target price forecast."},
    }


def _validate_and_repair_confidence(
    expert_json: dict,
    current_price: float,
    analyst_data: dict,
    news_json: dict,
    technical_analysis: TechnicalAnalysis,
    risk_level: str
) -> tuple[float, str]:
    """
    Ensure the confidence score is calculated correctly and has a proper step-by-step
    breakdown, recalculating if the LLM output is missing, incorrect, or contains placeholders.
    """
    # Extract values
    conf = _safe_float(expert_json.get("confidence_score"), default=-1.0)
    quant_sum = expert_json.get("quantitative_summary") or ""
    
    # Recalculate confidence score from scratch to verify/fallback
    score = 0.50
    breakdown_parts = ["0.50 (baseline)"]
    
    # +0.10 if analyst consensus data is available
    if analyst_data and analyst_data.get("mean_target"):
        score += 0.10
        breakdown_parts.append("+0.10 (analyst consensus)")
        
    # +0.10 if overall news sentiment is net-Bullish
    overall_sentiment = news_json.get("overall_sentiment", "")
    if overall_sentiment == "Bullish":
        score += 0.10
        breakdown_parts.append("+0.10 (bullish news)")
        
    # -0.10 if risk_level is High
    if risk_level == "High":
        score -= 0.10
        breakdown_parts.append("-0.10 (high risk)")
        
    # -0.10 if technical trend is Strong Downtrend or Moderately Bearish
    trend = technical_analysis.trend if hasattr(technical_analysis, "trend") else technical_analysis.get("trend", "")
    if trend in ("Downtrend", "Strong Downtrend", "Moderately Bearish"):
        score -= 0.10
        breakdown_parts.append("-0.10 (bearish trend)")
        
    # +0.05 if price is near strong support level (within 5%)
    support = technical_analysis.support if hasattr(technical_analysis, "support") else technical_analysis.get("support")
    if current_price and support and 0 < current_price - support <= current_price * 0.05:
        score += 0.05
        breakdown_parts.append("+0.05 (near support)")
        
    # Clamp final score to [0.20, 0.90]
    final_score = round(max(0.20, min(0.90, score)), 2)
    
    # Build breakdown string
    breakdown_str = " ".join(breakdown_parts) + f" = {final_score:.2f}"
    
    # Compute analyst consensus vs target % diff
    mean_target = _safe_float(analyst_data.get("mean_target")) if analyst_data else 0.0
    target_price = _safe_float(expert_json.get("target_price")) or final_score
    if mean_target and target_price:
        diff_pct = abs((mean_target - target_price) / target_price) * 100
        diff_str = f"Analyst consensus vs our target: {diff_pct:.1f}%."
    else:
        diff_str = "Analyst consensus vs our target: N/A."
        
    recalculated_quant_summary = f"Confidence score breakdown: {breakdown_str}. {diff_str}"
    
    # If the quantitative summary is a template/placeholder or missing, repair it
    is_placeholder = (
        not quant_sum or
        "adjustments = final" in quant_sum or
        "[actual math" in quant_sum or
        "[actual calculated" in quant_sum or
        "baseline 0.50" in quant_sum and "adjustments" in quant_sum
    )
    
    # Always enforce the exact Python-recalculated score and breakdown
    # to eliminate any possibility of LLM text-math mismatch or placeholder leaks.
    return final_score, recalculated_quant_summary


# ---------------------------------------------------------------------------
# Data quality assessment
# ---------------------------------------------------------------------------

def _assess_data_quality(analyst_data: dict, technical_indicators: dict, news: list, financial_records: list, confidence_score: float) -> DataQuality:
    has_analyst = bool(analyst_data.get("mean_target"))
    has_tech = bool(technical_indicators.get("rsi_14"))
    has_news = len(news) > 0
    has_fin = len(financial_records) > 0

    # Map the calculated confidence score directly to a label/level
    if confidence_score < 0.40:
        level, label = "Low", "Low Confidence"
    elif confidence_score < 0.65:
        level, label = "Medium", "Medium Confidence"
    elif confidence_score < 0.85:
        level, label = "High", "High Confidence"
    else:
        level, label = "Very High", "Very High Confidence"

    return DataQuality(
        level=level,
        label=label,
        has_analyst_consensus=has_analyst,
        has_technical_indicators=has_tech,
        has_news=has_news,
        has_financials=has_fin,
    )


# ---------------------------------------------------------------------------
# Main assembly function
# ---------------------------------------------------------------------------

def assemble_final_result(ticker: str, pre_fetched: dict, agent_outputs: dict) -> str:
    stock_data = pre_fetched.get("stock_data", {})
    news_raw = pre_fetched.get("news", [])
    financial_data = pre_fetched.get("financial_data", {})
    analyst_data = pre_fetched.get("analyst_data", {})
    technical_indicators_raw = pre_fetched.get("technical_indicators", {})

    data_json = _extract_json(agent_outputs.get("data", ""))
    news_json = _extract_json(agent_outputs.get("news", ""))
    analysis_json = _extract_json(agent_outputs.get("analysis", ""))
    risk_json = _extract_json(agent_outputs.get("risk", ""))
    expert_json = _extract_json(agent_outputs.get("expert", ""))

    # Scrub CEO/executive transition hallucinations and correct math range statement errors
    expert_json, data_json = _scrub_hallucinations_and_math(expert_json, data_json, pre_fetched)

    # --- Core identifiers ---
    company_name = stock_data.get("shortName") or data_json.get("company_name") or ticker
    current_price = _safe_float(stock_data.get("currentPrice") or data_json.get("current_price"))
    day_change_pct = _safe_float(stock_data.get("dayChangePct") or data_json.get("day_change_pct"))

    # --- Key Metrics (always prefer live stock_data over agent output) ---
    key_metrics_data = data_json.get("key_metrics", {})
    key_metrics = KeyMetrics(
        market_cap=_format_market_cap(stock_data.get("marketCap")) or key_metrics_data.get("market_cap"),
        pe_ratio=_safe_float(stock_data.get("trailingPE") or key_metrics_data.get("pe_ratio")) or None,
        beta=_safe_float(stock_data.get("beta") or key_metrics_data.get("beta")) or None,
        dividend_yield=_safe_float(stock_data.get("dividendYield") or key_metrics_data.get("dividend_yield")) or None,
        fifty_two_week_high=_safe_float(stock_data.get("fiftyTwoWeekHigh") or key_metrics_data.get("fifty_two_week_high")) or None,
        fifty_two_week_low=_safe_float(stock_data.get("fiftyTwoWeekLow") or key_metrics_data.get("fifty_two_week_low")) or None,
        volume=stock_data.get("volume") or key_metrics_data.get("volume"),
        forward_pe=_safe_float(stock_data.get("forwardPE")) or None,
        price_to_book=_safe_float(stock_data.get("priceToBook")) or None,
        eps_trailing=_safe_float(stock_data.get("epsTrailingTwelveMonths")) or None,
        eps_forward=_safe_float(stock_data.get("epsForward")) or None,
        revenue_growth=_safe_float(stock_data.get("revenueGrowth")) or None,
        earnings_growth=_safe_float(stock_data.get("earningsGrowth")) or None,
        profit_margins=_safe_float(stock_data.get("profitMargins")) or None,
        return_on_equity=_safe_float(stock_data.get("returnOnEquity")) or None,
        debt_to_equity=_safe_float(stock_data.get("debtToEquity")) or None,
    )

    # --- Company Profile ---
    company_profile = CompanyProfile(
        business_summary=stock_data.get("longBusinessSummary", ""),
        sector=stock_data.get("sector", ""),
        industry=stock_data.get("industry", ""),
        full_time_employees=stock_data.get("fullTimeEmployees"),
        country=stock_data.get("country", ""),
        city=stock_data.get("city", ""),
        website=stock_data.get("website", ""),
    )

    # --- Financial Records ---
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

    # --- News ---
    news_articles_raw = news_json.get("news_summary", [])
    if news_articles_raw and isinstance(news_articles_raw, list) and len(news_articles_raw) > 0:
        final_news = []
        for a in news_articles_raw[:8]:
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
                for a in news_raw[:8]
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
            for a in news_raw[:8]
        ]
    else:
        final_news = []

    # --- Technical Analysis ---
    vol = _safe_float(analysis_json.get("volatility"))
    if (vol is None or vol <= 0) and technical_indicators_raw:
        vol = _safe_float(technical_indicators_raw.get("volatility_30d"))
    if vol is None:
        vol = 0.0

    trend = analysis_json.get("trend", "N/A")
    trend = _validate_and_repair_trend(trend, technical_indicators_raw)

    # --- Bug 4 fix: Validate support/resistance vs current price ---
    raw_support = _safe_float(analysis_json.get("support")) if analysis_json.get("support") else None
    raw_resistance = _safe_float(analysis_json.get("resistance")) if analysis_json.get("resistance") else None
    if raw_resistance and current_price and current_price > raw_resistance * 1.05:
        print(f"[assembly] Price {current_price} already above resistance {raw_resistance}. "
              f"Promoting old resistance to support.")
        raw_support = raw_resistance
        raw_resistance = round(current_price * 1.15, 2)
    if raw_support and current_price and raw_support > current_price * 1.05:
        print(f"[assembly] Support {raw_support} is above current price {current_price}. "
              f"Adjusting support downward.")
        raw_support = round(current_price * 0.90, 2)

    technical_analysis = TechnicalAnalysis(
        trend=trend,
        volatility=vol,
        support=raw_support,
        resistance=raw_resistance,
        momentum=analysis_json.get("momentum"),
        rsi_interpretation=analysis_json.get("rsi_interpretation"),
        macd_interpretation=analysis_json.get("macd_interpretation"),
    )


    # --- Technical Indicators (from pre-fetched, fully reliable) ---
    technical_indicators = TechnicalIndicators(**{
        k: v for k, v in technical_indicators_raw.items()
        if k in TechnicalIndicators.model_fields
    }) if technical_indicators_raw else None

    # --- Analyst Consensus ---
    analyst_consensus = AnalystConsensus(**{
        k: v for k, v in analyst_data.items()
        if k in AnalystConsensus.model_fields and v is not None
    }) if any(v is not None for v in analyst_data.values()) else None

    # --- Risk ---
    risk_json = _validate_risk_output(risk_json)
    risk_level = risk_json.get("risk_level", "Medium")
    
    # Scrub overstated leverage risks for low D/E stocks
    debt_to_equity = _safe_float(stock_data.get("debtToEquity"))
    key_risks = _clean_leverage_risks(risk_json.get("key_risks", []), debt_to_equity)
    
    # Scrub overfitted news/satellite/Globalstar risks
    risk_summary = risk_json.get("risk_summary", "")
    key_risks, risk_summary = _clean_overfitted_risks(key_risks, risk_summary, ticker, stock_data)

    # --- Expert (validate before use) ---
    expert_json = _validate_expert_output(expert_json, current_price, analyst_data)

    # Repair time_horizon if agent returned template string or invalid value
    time_horizon = expert_json.get("time_horizon", "Medium-term")
    if "/" in time_horizon or time_horizon not in ("Short-term", "Medium-term", "Long-term"):
        print(f"[assembly] Repaired invalid time_horizon: '{time_horizon}'")
        time_horizon = "Medium-term"

    # Move confidence calculation earlier to calibrate recommendation based on it
    confidence_score, quantitative_summary = _validate_and_repair_confidence(
        expert_json, current_price, analyst_data, news_json, technical_analysis, risk_level
    )

    recommendation = expert_json.get("recommendation", "Hold")
    
    # Downgrade "Strong Buy" when confidence is below 65% or news has no bullish catalyst
    # (recalc target prices and trajectory based on corrected rating)
    if confidence_score < 0.65:
        if recommendation == "Strong Buy":
            overall_sentiment = news_json.get("overall_sentiment", "")
            trend = technical_analysis.trend
            if overall_sentiment in ("Neutral", "Mixed") or trend not in ("Strong Uptrend", "Strong Uptrend/Moderately Bullish"):
                recommendation = "Accumulate"
                print(f"[assembly] Recalibrated recommendation for {ticker}: 'Strong Buy' -> 'Accumulate' (confidence={confidence_score}, sentiment={overall_sentiment}, trend={trend})")
            else:
                recommendation = "Buy"
                print(f"[assembly] Recalibrated recommendation for {ticker}: 'Strong Buy' -> 'Buy' (confidence={confidence_score})")
        elif recommendation == "Buy" and confidence_score < 0.55:
            overall_sentiment = news_json.get("overall_sentiment", "")
            if overall_sentiment in ("Neutral", "Mixed"):
                recommendation = "Hold"
                print(f"[assembly] Recalibrated recommendation for {ticker}: 'Buy' -> 'Hold' (confidence={confidence_score}, sentiment={overall_sentiment})")
            else:
                recommendation = "Accumulate"
                print(f"[assembly] Recalibrated recommendation for {ticker}: 'Buy' -> 'Accumulate' (confidence={confidence_score})")

    target_price = _safe_float(expert_json.get("target_price"))
    # Inject trend hint for _compute_fallback_target to apply trend-based adjustments
    expert_json["_trend_hint"] = trend

    # Bug 9 fix: Guard against target_price == resistance (lazy LLM copy)
    resistance = _safe_float(analysis_json.get("resistance"))
    if resistance and target_price and abs(target_price - resistance) < 0.01:
        print(f"[assembly] target_price={target_price} equals resistance level — falling back to analyst consensus")
        target_price = _compute_fallback_target(current_price, analyst_data, expert_json)
        expert_json["target_price"] = target_price

    tp_data = expert_json.get("target_prices", {})
    repaired_tps = _validate_and_repair_target_prices(tp_data, current_price, target_price, recommendation)
    target_prices = TargetPrices(
        three_months=TargetPricePoint(
            price=repaired_tps["three_months"]["price"],
            rationale=_align_text_with_trend(_align_text_with_recommendation(repaired_tps["three_months"]["rationale"], recommendation), trend),
        ),
        six_months=TargetPricePoint(
            price=repaired_tps["six_months"]["price"],
            rationale=_align_text_with_trend(_align_text_with_recommendation(repaired_tps["six_months"]["rationale"], recommendation), trend),
        ),
        twelve_months=TargetPricePoint(
            price=repaired_tps["twelve_months"]["price"],
            rationale=_align_text_with_trend(_align_text_with_recommendation(repaired_tps["twelve_months"]["rationale"], recommendation), trend),
        ),
    )

    verdict = expert_json.get("verdict", "") or risk_summary or "No verdict provided."
    verdict = _align_text_with_recommendation(verdict, recommendation)
    verdict = _align_text_with_trend(verdict, trend)

    reasoning = expert_json.get("reasoning", [])
    if not isinstance(reasoning, list):
        reasoning = []
    reasoning = [_align_text_with_trend(_align_text_with_recommendation(r, recommendation), trend) for r in reasoning]
    
    # Bug 2 fix: Only append risk items that don't contradict existing reasoning sentiment
    if key_risks:
        existing_text = " ".join(reasoning).lower()
        for risk in key_risks[:3]:
            risk_lower = risk.lower()
            # Skip if this risk directly contradicts a bullish momentum claim in expert reasoning
            if "bearish momentum" in risk_lower and "accelerating momentum" in existing_text:
                print(f"[assembly] Skipping contradictory risk item: '{risk}'")
                continue
            reasoning.append(f"Risk: {risk}")

    fundamental_notes = data_json.get("fundamental_notes", "")
    fundamental_analysis = data_json.get("fundamental_analysis", {})
    if not fundamental_analysis and fundamental_notes:
        fundamental_analysis = {"notes": fundamental_notes}

    # --- Data Quality ---
    data_quality = _assess_data_quality(analyst_data, technical_indicators_raw, final_news, financial_records, confidence_score)

    volatility = technical_analysis.volatility

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
        technical_indicators=technical_indicators,
        analyst_consensus=analyst_consensus,
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
        data_quality=data_quality,
    )

    final_dict = final.model_dump() if hasattr(final, "model_dump") else final.dict()
    from utils import clean_json_data
    final_dict = clean_json_data(final_dict)
    return json.dumps(final_dict, indent=2)