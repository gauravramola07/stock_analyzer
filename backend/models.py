from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


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


class TechnicalAnalysis(BaseModel):
    trend: str
    volatility: float
    support: Optional[float] = None
    resistance: Optional[float] = None


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
    fundamental_analysis: Dict[str, Any] = Field(default_factory=dict)
    recommendation: str
    target_price: float
    target_prices: Optional[TargetPrices] = None
    time_horizon: str
    confidence_score: float
    risk_level: str
    verdict: str
    quantitative_summary: Optional[str] = None
    reasoning: List[str] = Field(default_factory=list)

    class Config:
        extra = "allow"