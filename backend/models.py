from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class TickerRequest(BaseModel):
    ticker: str

class NewsArticle(BaseModel):
    title: str
    source: str
    date: str
    sentiment: str  # Bullish, Bearish, Neutral
    summary: str
    url: Optional[str] = None

class KeyMetrics(BaseModel):
    market_cap: Optional[str] = None
    pe_ratio: Optional[float] = None
    beta: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    volume: Optional[int] = None

class TechnicalAnalysis(BaseModel):
    trend: str
    volatility: float
    support: Optional[float] = None
    resistance: Optional[float] = None

class FinalVerdict(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    day_change_pct: float
    volatility: float
    key_metrics: Dict
    news_summary: List[NewsArticle]
    technical_analysis: Dict
    fundamental_analysis: Dict
    recommendation: str # Buy | Hold | Avoid
    target_price: float
    time_horizon: str # Short-term | Medium-term | Long-term
    confidence_score: float
    risk_level: str # Low | Medium | High
    verdict: str
    reasoning: List[str]
