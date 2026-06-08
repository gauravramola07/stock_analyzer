from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal


class TickerRequest(BaseModel):
    ticker: str


class NewsArticle(BaseModel):
    title: str
    source: str
    date: str
    sentiment: str
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
    forward_pe: Optional[float] = None
    price_to_book: Optional[float] = None
    eps_trailing: Optional[float] = None
    eps_forward: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    profit_margins: Optional[float] = None
    return_on_equity: Optional[float] = None
    debt_to_equity: Optional[float] = None


class TechnicalAnalysis(BaseModel):
    trend: Literal[
        "Strong Uptrend", "Moderately Bullish", "Sideways / Consolidation",
        "Moderately Bearish", "Strong Downtrend", "N/A"
    ] = "N/A"
    volatility: float
    support: Optional[float] = None
    resistance: Optional[float] = None
    momentum: Optional[str] = None
    rsi_interpretation: Optional[str] = None
    macd_interpretation: Optional[str] = None


class TechnicalIndicators(BaseModel):
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_crossover: Optional[str] = None
    bb_upper: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_position: Optional[float] = None
    price_vs_sma20: Optional[str] = None
    price_vs_sma50: Optional[str] = None
    rsi_signal: Optional[str] = None
    fifty_two_week_position: Optional[float] = None
    avg_volume_ratio: Optional[float] = None
    volatility_30d: Optional[float] = None



class AnalystConsensus(BaseModel):
    mean_target: Optional[float] = None
    high_target: Optional[float] = None
    low_target: Optional[float] = None
    median_target: Optional[float] = None
    num_analysts: Optional[int] = None
    recommendation_key: Optional[str] = None
    recommendation_mean: Optional[float] = None
    strong_buy: Optional[int] = None
    buy: Optional[int] = None
    hold: Optional[int] = None
    sell: Optional[int] = None
    strong_sell: Optional[int] = None


class TargetPricePoint(BaseModel):
    price: float
    rationale: Optional[str] = None


class TargetPrices(BaseModel):
    three_months: Optional[TargetPricePoint] = None
    six_months: Optional[TargetPricePoint] = None
    twelve_months: Optional[TargetPricePoint] = None


class CompanyProfile(BaseModel):
    business_summary: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    full_time_employees: Optional[int] = None
    country: Optional[str] = None
    city: Optional[str] = None
    website: Optional[str] = None


class FinancialRecord(BaseModel):
    period: str
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    gross_profit: Optional[float] = None
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    source: Optional[str] = None


class DataQuality(BaseModel):
    level: str  # "High" | "Medium" | "Low"
    label: str  # Human readable label
    has_analyst_consensus: bool = False
    has_technical_indicators: bool = False
    has_news: bool = False
    has_financials: bool = False


class FinalVerdict(BaseModel):
    ticker: str
    company_name: str
    current_price: float
    day_change_pct: float
    volatility: float
    key_metrics: KeyMetrics
    company_profile: Optional[CompanyProfile] = None
    financial_records: List[FinancialRecord] = Field(default_factory=list)
    news_summary: List[NewsArticle] = Field(default_factory=list)
    technical_analysis: TechnicalAnalysis
    technical_indicators: Optional[TechnicalIndicators] = None
    analyst_consensus: Optional[AnalystConsensus] = None
    fundamental_analysis: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Literal["Strong Buy", "Buy", "Speculative Buy", "Accumulate", "Hold", "Avoid"]
    target_price: float
    target_prices: Optional[TargetPrices] = None
    time_horizon: str
    confidence_score: float
    risk_level: Literal["Low", "Medium", "High"]
    verdict: str
    quantitative_summary: Optional[str] = None
    reasoning: List[str] = Field(default_factory=list)
    data_quality: Optional[DataQuality] = None

    class Config:
        extra = "allow"