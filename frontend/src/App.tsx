import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  Search, TrendingUp, TrendingDown, Newspaper, ShieldAlert,
  BarChart4, Target, Info, Building2,
  FileText, ExternalLink, Zap, ArrowLeft, ChevronRight,
} from 'lucide-react';
import { useTheme } from './hooks/useTheme';
import { useAnimatedNumber } from './hooks/useAnimatedNumber';
import ThreeHero from './components/ThreeHero';
import ThemeToggle from './components/ThemeToggle';
import TickerStrip from './components/TickerStrip';
import SkeletonCard from './components/SkeletonCard';
import WorkflowPipeline from './components/WorkflowPipeline';
import CustomTooltip from './components/CustomTooltip';
import SectionHeader from './components/SectionHeader';
import MetricRow from './components/MetricRow';
import DataCell from './components/DataCell';
import NewsCard from './components/NewsCard';
import ReasoningItem from './components/ReasoningItem';
import EmptyState from './components/EmptyState';

export type ViewState = 'landing' | 'select' | 'dashboard';
export type PhaseStatus = 'idle' | 'running' | 'done';

export interface NewsArticle {
  title: string;
  source: string;
  date: string;
  sentiment: string;
  summary: string;
  url?: string;
}

interface TargetPoint {
  price?: number;
  rationale?: string;
}

interface CompanyProfile {
  business_summary?: string;
  sector?: string;
  industry?: string;
  full_time_employees?: number;
  country?: string;
  city?: string;
  website?: string;
}

interface FinancialRecord {
  period: string;
  revenue?: number;
  net_income?: number;
  gross_profit?: number;
  total_assets?: number;
  total_debt?: number;
  operating_cash_flow?: number;
  source?: string;
}

interface KeyMetrics {
  market_cap?: string;
  pe_ratio?: number;
  forward_pe?: number;
  price_to_book?: number;
  eps_trailing?: number;
  beta?: number;
  dividend_yield?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
  volume?: number;
  revenue_growth?: number;
  earnings_growth?: number;
  profit_margins?: number;
  return_on_equity?: number;
  debt_to_equity?: number;
}

interface TechnicalAnalysis {
  trend?: string;
  volatility?: number;
  support?: number;
  resistance?: number;
  momentum?: string;
  rsi_interpretation?: string;
  macd_interpretation?: string;
}

interface TechnicalIndicators {
  sma_20?: number;
  sma_50?: number;
  rsi_14?: number;
  macd_line?: number;
  macd_signal?: number;
  macd_histogram?: number;
  macd_crossover?: string;
  bb_upper?: number;
  bb_lower?: number;
  bb_position?: number;
  price_vs_sma20?: string;
  price_vs_sma50?: string;
  rsi_signal?: string;
  fifty_two_week_position?: number;
  avg_volume_ratio?: number;
}

interface AnalystConsensus {
  mean_target?: number;
  high_target?: number;
  low_target?: number;
  num_analysts?: number;
  recommendation_key?: string;
  strong_buy?: number;
  buy?: number;
  hold?: number;
  sell?: number;
  strong_sell?: number;
}

interface DataQuality {
  level?: string;
  label?: string;
  has_analyst_consensus?: boolean;
  has_technical_indicators?: boolean;
  has_news?: boolean;
  has_financials?: boolean;
}

interface TargetPrices {
  three_months?: TargetPoint;
  six_months?: TargetPoint;
  twelve_months?: TargetPoint;
}

export interface FinalData {
  ticker: string;
  company_name?: string;
  current_price?: number;
  day_change_pct?: number;
  volatility?: number;
  recommendation?: string;
  verdict?: string;
  quantitative_summary?: string;
  time_horizon?: string;
  confidence_score?: number;
  risk_level?: string;
  key_metrics?: KeyMetrics;
  company_profile?: CompanyProfile;
  financial_records?: FinancialRecord[];
  technical_analysis?: TechnicalAnalysis;
  technical_indicators?: TechnicalIndicators;
  analyst_consensus?: AnalystConsensus;
  data_quality?: DataQuality;
  target_price?: number;
  target_prices?: TargetPrices;
  news_summary?: NewsArticle[];
  reasoning?: string[];
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

function formatLargeNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
  const numVal = Number(val);
  const isNegative = numVal < 0;
  const n = Math.abs(numVal);
  const prefix = isNegative ? '-$' : '$';
  if (n >= 1e12) return `${prefix}${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${prefix}${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${prefix}${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${prefix}${(n / 1e3).toFixed(1)}K`;
  return `${prefix}${n.toFixed(0)}`;
}


function formatNum(val: unknown, decimals = 2): string {
  if (val === null || val === undefined || Number.isNaN(Number(val))) return '—';
  return Number(val).toFixed(decimals);
}

const EASE_OUT = [0.22, 1, 0.36, 1] as [number, number, number, number];

const pageIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: EASE_OUT } },
  exit: { opacity: 0, y: -10, transition: { duration: 0.25 } },
};

const staggerWrap = {
  animate: { transition: { staggerChildren: 0.06, delayChildren: 0.08 } },
};

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE_OUT } },
};

const fadeScale = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.4, ease: EASE_OUT } },
};

interface TickerItem {
  symbol: string;
  name: string;
}

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const [view, setView] = useState<ViewState>('landing');
  const [query, setQuery] = useState('');
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const [allTickersLoaded, setAllTickersLoaded] = useState(false);
  const [tickerCount, setTickerCount] = useState(0);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [data, setData] = useState<FinalData | null>(null);
  const [history, setHistory] = useState<{ date: string; price: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [activePhases, setActivePhases] = useState<Record<string, PhaseStatus>>({
    prefetch: 'idle', data: 'idle', news: 'idle', analysis: 'idle',
    risk: 'idle', expert: 'idle', complete: 'idle',
  });
  const dataReceivedRef = useRef(false);
 
useEffect(() => {
    axios.get(`${API_BASE}/tickers`)
      .then((res) => {
        const data = res.data;
        setTickers(data.tickers || []);
        setTickerCount(data.count || (data.tickers || []).length);
        setAllTickersLoaded(true);
      })
      .catch(() => {
        const fallbackSymbols = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'AMZN', 'GOOGL', 'META', 'AMD', 'NFLX', 'CRM', 'ADBE', 'PYPL', 'UBER', 'COIN', 'INTC', 'DIS', 'BA', 'JPM', 'V', 'MA', 'WMT', 'KO', 'PEP', 'PFE', 'JNJ', 'XOM', 'CVX', 'GS', 'IBM', 'ORCL', 'CRM', 'NOW', 'SNOW', 'PLTR', 'RDDT', 'ARM', 'SMCI', 'DDOG', 'NET', 'FSLY'];
        const fallbackNames: Record<string, string> = {
          AAPL: "Apple Inc.", NVDA: "NVIDIA Corporation", TSLA: "Tesla, Inc.",
          MSFT: "Microsoft Corporation", AMZN: "Amazon.com, Inc.", GOOGL: "Alphabet Inc.",
          META: "Meta Platforms, Inc.", AMD: "Advanced Micro Devices, Inc.", NFLX: "Netflix, Inc.",
          CRM: "Salesforce, Inc.", ADBE: "Adobe Inc.", PYPL: "PayPal Holdings, Inc.",
          UBER: "Uber Technologies, Inc.", COIN: "Coinbase Global, Inc.", INTC: "Intel Corporation",
          DIS: "The Walt Disney Company", BA: "The Boeing Company", JPM: "JPMorgan Chase & Co.",
          V: "Visa Inc.", MA: "Mastercard Incorporated", WMT: "Walmart Inc.",
          KO: "The Coca-Cola Company", PEP: "PepsiCo, Inc.", PFE: "Pfizer Inc.",
          JNJ: "Johnson & Johnson", XOM: "Exxon Mobil Corporation", CVX: "Chevron Corporation",
          GS: "The Goldman Sachs Group, Inc.", IBM: "International Business Machines Corporation",
          ORCL: "Oracle Corporation", NOW: "ServiceNow, Inc.", SNOW: "Snowflake Inc.",
          PLTR: "Palantir Technologies Inc.", RDDT: "Reddit, Inc.", ARM: "Arm Holdings plc",
          SMCI: "Super Micro Computer, Inc.", DDOG: "Datadog, Inc.", NET: "Cloudflare, Inc.",
          FSLY: "Fastly, Inc."
        };
        setTickers(fallbackSymbols.map(s => ({ symbol: s, name: fallbackNames[s] || s })));
      });
  }, []);

  const filteredTickers = useMemo(() => {
    const q = query.trim().toUpperCase();
    return q
      ? tickers.filter((t) => t.symbol.toUpperCase().includes(q) || t.name.toUpperCase().includes(q))
      : tickers;
  }, [query, tickers]);

  // When searching, show ALL matches. When browsing, show a scrollable subset.
  const BROWSE_LIMIT = 500;
  const visibleTickers = query.trim() ? filteredTickers : filteredTickers.slice(0, BROWSE_LIMIT);

  const handleSelectTicker = useCallback(async (symbol: string) => {
    setSelectedTicker(symbol);
    setView('dashboard');
    setLoading(true);
    setError('');
    setData(null);
    setLogs([]);
    setActivePhases({
      prefetch: 'idle', data: 'idle', news: 'idle', analysis: 'idle',
      risk: 'idle', expert: 'idle', complete: 'idle',
    });
    dataReceivedRef.current = false;

    try {
      const histRes = await axios.get(`${API_BASE}/stock/${symbol}/history`);
      setHistory(histRes.data.history || []);

      const es = new EventSource(`${API_BASE}/analyze/stream/${symbol}`);
      // Track last real-data activity to distinguish genuine disconnections
      // from transient reconnects that happen after SSE keep-alive comments.
      let lastActivity = Date.now();

      es.addEventListener('log', (e: MessageEvent) => {
        lastActivity = Date.now();
        setLogs((prev) => [...prev.slice(-12), String(e.data)]);
      });

      es.addEventListener('phase', (e: MessageEvent) => {
        lastActivity = Date.now();
        try {
          const payload = JSON.parse(String(e.data));
          setActivePhases((prev) => ({
            ...prev,
            [payload.step]: payload.status === 'done' ? 'done' : 'running',
          }));
        } catch { /* ignore */ }
      });

      es.addEventListener('final_result', (e: MessageEvent) => {
        try {
          dataReceivedRef.current = true;
          setData(JSON.parse(String(e.data)));
          setActivePhases((prev) => ({ ...prev, complete: 'done' }));
        } catch {
          setError('Server returned data that could not be parsed.');
        } finally {
          setLoading(false);
          es.close();
        }
      });

      es.addEventListener('error', (e: MessageEvent) => {
        setError(String(e.data) || 'An error occurred during analysis.');
        setLoading(false);
        es.close();
      });

      es.onerror = () => {
        // readyState 0 = CONNECTING (browser auto-reconnecting — normal for SSE keep-alives)
        // readyState 1 = OPEN (still connected)
        // readyState 2 = CLOSED (truly dead connection)
        if (es.readyState === EventSource.CLOSED) {
          setLoading(false);
          es.close();
          if (!dataReceivedRef.current) {
            // Only show error if we've been idle for >5s (i.e., not a brief reconnect)
            const idleMs = Date.now() - lastActivity;
            if (idleMs > 5000) {
              setError('Stream closed before final result was returned.');
            }
          }
        }
        // If CONNECTING, the browser will retry automatically — do nothing
      };
    } catch (err: any) {
      setLoading(false);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load ticker data.');
    }
  }, []);

  const minPrice = history.length ? Math.min(...history.map((h) => h.price)) : 0;
  const maxPrice = history.length ? Math.max(...history.map((h) => h.price)) : 0;
  const isPositive = Number(data?.day_change_pct || 0) >= 0;

  const resetToSelect = () => {
    setView('select');
    setData(null);
    setError('');
    setLogs([]);
  };

  const animatedPrice = useAnimatedNumber(data?.current_price, 800, 2);
  const animatedChange = useAnimatedNumber(data?.day_change_pct, 600, 2);
  const animatedTarget = useAnimatedNumber(data?.target_price, 800, 2);
  const animatedConfidence = useAnimatedNumber(data?.confidence_score ? data.confidence_score * 100 : undefined, 600, 1);

  return (
    <div className="aura-bg">

      {view === 'landing' && (
        <div
          style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', position: 'relative', zIndex: 10 }}
        >
            <ThreeHero />

            <motion.div
              variants={staggerWrap}
              initial="initial"
              animate="animate"
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '80px 24px 60px',
                position: 'relative',
                zIndex: 10,
              }}
            >
              <div style={{ maxWidth: 720, width: '100%', textAlign: 'center' }}>
                <motion.div variants={fadeUp} style={{ marginBottom: 32 }}>
                  <div className="eyebrow-badge">
                    <motion.span
                      style={{
                        width: 6, height: 6, borderRadius: '50%',
                        background: 'var(--accent)', display: 'inline-block',
                      }}
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ repeat: Infinity, duration: 1.4, ease: 'easeInOut' }}
                    />
                    AI-POWERED EQUITY INTELLIGENCE
                  </div>
                </motion.div>

                <motion.h1
                  variants={fadeUp}
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: 'clamp(48px, 8vw, 88px)',
                    fontWeight: 800,
                    letterSpacing: '-0.03em',
                    lineHeight: 0.95,
                    color: 'var(--text-primary)',
                    marginBottom: 32,
                    textShadow: '0 0 80px rgba(0,0,0,0.5)',
                  }}
                >
                  STOCK
                  <br />
                  <span style={{ color: 'var(--accent)' }}>INTELLIGENCE</span>
                </motion.h1>

                <motion.p
                  variants={fadeUp}
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 13,
                    color: 'var(--text-secondary)',
                    letterSpacing: '0.04em',
                    marginBottom: 48,
                    lineHeight: 2,
                  }}
                >
                  &gt; Multi-agent pipeline — market data, sentiment analysis,
                  <br />
                  technical signals &amp; equity verdict streamed live._
                  <motion.span
                    style={{ display: 'inline-block', width: 7, height: 13, background: 'var(--accent)', marginLeft: 4, verticalAlign: 'middle', borderRadius: 1 }}
                    animate={{ opacity: [1, 0, 1] }}
                    transition={{ repeat: Infinity, duration: 0.9 }}
                  />
                </motion.p>

                <motion.div variants={fadeUp}>
                  <motion.button
                    className="cta-btn"
                    onClick={() => setView('select')}
                    whileHover={{ scale: 1.03, y: -1 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    INITIALIZE SYSTEM
                    <ChevronRight size={16} />
                  </motion.button>
                </motion.div>

                <motion.div
                  variants={fadeUp}
                  style={{
                    marginTop: 64,
                    display: 'flex',
                    justifyContent: 'center',
                    gap: 60,
                    flexWrap: 'wrap',
                  }}
                >
                  {[
                    { value: '7', label: 'AGENTS' },
                    { value: '4+', label: 'DATA SOURCES' },
                    { value: '<30s', label: 'LATENCY' },
                  ].map((stat) => (
                    <div key={stat.label} style={{ textAlign: 'center' }}>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 28, fontWeight: 700, color: 'var(--accent)',
                        textShadow: '0 0 30px var(--accent-glow)',
                      }}>
                        {stat.value}
                      </div>
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, letterSpacing: '0.22em',
                        color: 'var(--text-muted)', marginTop: 6,
                      }}>
                        {stat.label}
                      </div>
                    </div>
                  ))}
                </motion.div>
              </div>
            </motion.div>

            <TickerStrip />

            <div className="status-bar">
              <span>SYS::ONLINE</span>
              <span style={{ color: 'var(--accent)', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <motion.span
                  style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)', display: 'inline-block' }}
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ repeat: Infinity, duration: 1.4 }}
                />
                READY
              </span>
              <span>v2.0.0</span>
            </div>
          </div>
        )}

        {view === 'select' && (
          <div
            style={{
              maxWidth: 1080, margin: '0 auto',
              padding: '48px 24px 80px',
              position: 'relative', zIndex: 10,
              minHeight: '100vh',
            }}
          >
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 32, flexWrap: 'wrap', gap: 12 }}
            >
              <button className="back-btn" onClick={() => setView('landing')}>
                <ArrowLeft size={14} /> BACK
              </button>
              <span style={{
                fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                letterSpacing: '0.18em', color: 'var(--text-muted)',
              }}>
                &gt; SELECT_TICKER /
                <span style={{ color: 'var(--accent)' }}> {tickerCount} TOTAL · {filteredTickers.length} MATCHED</span>
              </span>
              <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="terminal-input"
              style={{ marginBottom: 20, maxWidth: 720, margin: '0 auto 20px' }}
            >
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 14, color: 'var(--accent)', userSelect: 'none',
              }}>$</span>
              <Search size={15} style={{ color: 'var(--text-muted)' }} />
              <input
                placeholder="Search ticker symbol..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Search ticker symbol"
              />
              <span style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em',
                userSelect: 'none',
              }}>
                {query.trim() ? `${filteredTickers.length} found` : `${tickerCount} total`}
              </span>
            </motion.div>

            {visibleTickers.length > 0 ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
                  gap: 10,
                  maxHeight: query.trim() ? '70vh' : '60vh',
                  overflowY: 'auto',
                  paddingRight: 8,
                  scrollbarWidth: 'thin',
                }}
              >
                {visibleTickers.map(({ symbol, name }) => (
                  <button
                    key={symbol}
                    className="void-card void-card-interactive"
                    onClick={() => handleSelectTicker(symbol)}
                    style={{ textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 4 }}
                  >
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 15, fontWeight: 700,
                      color: 'var(--text-primary)',
                    }}>
                      {symbol}
                    </div>
                    <div style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 10,
                      color: 'var(--text-muted)',
                      textOverflow: 'ellipsis',
                      overflow: 'hidden',
                      whiteSpace: 'nowrap',
                      width: '100%',
                    }} title={name}>
                      {name || 'Analyze'}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <EmptyState title="NO TICKERS FOUND" icon="search" />
            )}

            {!query.trim() && filteredTickers.length > BROWSE_LIMIT && (
              <div style={{
                textAlign: 'center', marginTop: 16,
                fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                color: 'var(--text-muted)', letterSpacing: '0.1em',
              }}>
                Showing {BROWSE_LIMIT} of {tickerCount} tickers — type to search for any ticker
              </div>
            )}

            <div className="status-bar">
              <span>SYS::ONLINE</span>
              <span style={{ color: 'var(--accent)' }}>● READY</span>
              <span>v2.0.0</span>
</div>
          </div>
        )}

        {view === 'dashboard' && (
          <div
            style={{
              maxWidth: 1400, margin: '0 auto',
              padding: '32px 24px 80px',
              position: 'relative', zIndex: 10,
              minHeight: '100vh',
            }}
          >
            <div style={{
              display: 'flex', alignItems: 'center',
              justifyContent: 'space-between', marginBottom: 24,
              flexWrap: 'wrap', gap: 12,
            }}>
              <button className="back-btn" onClick={resetToSelect}>
                <ArrowLeft size={14} /> CHANGE TICKER
              </button>

              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11, letterSpacing: '0.16em', color: 'var(--text-secondary)',
              }}>
                {loading && (
                  <motion.span
                    style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--accent)', display: 'inline-block',
                    }}
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                  />
                )}
                {selectedTicker
                  ? `ANALYZING :: ${selectedTicker}`
                  : 'NO TICKER SELECTED'}
              </div>

              <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
            </div>

            {loading && (
              <div
                className="pipeline-wrap"
                style={{ marginBottom: 24 }}
              >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28, flexWrap: 'wrap' }}>
                    <Zap size={16} style={{ color: 'var(--accent)' }} />
                    <span style={{
                      fontFamily: "'Inter', sans-serif", fontSize: 17,
                      fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-primary)',
                    }}>
                      AGENT PIPELINE
                    </span>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-secondary)',
                    }}>
                      {selectedTicker}
                    </span>
                  </div>

                  <WorkflowPipeline phases={activePhases} />

                  {logs.length > 0 && (
                    <div
                      className="log-container"
                      style={{ marginTop: 24 }}
                    >
                      <div style={{
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 9, letterSpacing: '0.22em',
                        color: 'var(--text-muted)', marginBottom: 10,
                      }}>
                        LIVE FEED
                      </div>

                      {logs.slice(-7).map((line, idx, arr) => (
                        <div key={idx} className="log-line">
                          <span className="log-prompt">&gt;</span>
                          {line}
                          {idx === arr.length - 1 && (
                            <motion.span
                              style={{
                                display: 'inline-block', background: 'var(--accent)',
                                width: 7, height: 13, marginLeft: 5,
                                verticalAlign: 'middle', borderRadius: 1,
                              }}
                              animate={{ opacity: [1, 0, 1] }}
                              transition={{ repeat: Infinity, duration: 0.9 }}
                            />
                          )}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}

            {loading && !data && (
              <div className="dashboard-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20, alignItems: 'start' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <SkeletonCard height={420} />
                  <SkeletonCard height={300} />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <SkeletonCard height={180} />
                  <SkeletonCard height={320} />
                </div>
              </div>
            )}

            {error && (
              <div
                style={{
                  background: 'rgba(244,63,94,0.06)',
                  border: '1px solid rgba(244,63,94,0.2)',
                  borderRadius: 12, padding: '14px 20px', marginBottom: 24,
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 13, color: '#f43f5e', letterSpacing: '0.04em',
                }}
              >
                <span style={{ marginRight: 8, opacity: 0.6 }}>ERROR::</span>
                {error}
              </div>
            )}

            {data && (
              <motion.div
                variants={staggerWrap}
                initial="initial"
                animate="animate"
                className="dashboard-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 300px',
                  gap: 20, alignItems: 'start',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <motion.div variants={fadeUp} className="void-card">
                    <div style={{
                      display: 'flex', justifyContent: 'space-between',
                      alignItems: 'flex-start', flexWrap: 'wrap',
                      gap: 16, marginBottom: 24,
                    }}>
                      <div>
                        <div className="section-label" style={{ marginBottom: 8 }}>
                          EQUITY DOSSIER
                        </div>
                        <h2 style={{
                          fontFamily: "'Inter', sans-serif", fontSize: 30,
                          fontWeight: 800, letterSpacing: '-0.025em',
                          color: 'var(--text-primary)', lineHeight: 1, marginBottom: 5,
                        }}>
                          {data.ticker}
                          {data.company_name && (
                            <span style={{
                              color: 'var(--text-secondary)', fontWeight: 600,
                              fontSize: 18, marginLeft: 10,
                            }}>
                              {data.company_name}
                            </span>
                          )}
                        </h2>
                        {(data.company_profile?.sector || data.company_profile?.industry) && (
                          <div style={{
                            fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 11, letterSpacing: '0.1em', color: 'var(--text-muted)',
                          }}>
                            {[data.company_profile.sector, data.company_profile.industry]
                              .filter(Boolean).join(' / ')}
                          </div>
                        )}
                      </div>

                      <div style={{
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 12, padding: '14px 20px', minWidth: 148,
                      }}>
                        <div className="section-label" style={{ marginBottom: 7 }}>
                          CURRENT PRICE
                        </div>
                        <div style={{
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 28, fontWeight: 700,
                          color: 'var(--text-primary)', lineHeight: 1,
                        }}>
                          ${animatedPrice}
                        </div>
                        <div style={{
                          display: 'flex', alignItems: 'center', gap: 4,
                          marginTop: 7,
                          fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 13, fontWeight: 600,
                          color: isPositive ? 'var(--gain)' : 'var(--loss)',
                        }}>
                          {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                          {isPositive ? '+' : ''}{animatedChange}%
                        </div>
                      </div>
                    </div>

                    <div style={{ height: 310 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={history} margin={{ top: 10, right: 4, left: 0, bottom: 0 }}>
                          <defs>
                            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="#00d975" stopOpacity={0.22} />
                              <stop offset="55%" stopColor="#00d975" stopOpacity={0.06} />
                              <stop offset="100%" stopColor="#00d975" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="2 6" stroke="rgba(var(--border-rgb), 0.04)" />
                          <XAxis
                            dataKey="date"
                            tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                            tickLine={false} axisLine={false}
                            tickFormatter={(v: string) => v?.slice(5) || ''}
                          />
                          <YAxis
                            tick={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}
                            tickLine={false} axisLine={false}
                            domain={[minPrice * 0.98, maxPrice * 1.02]}
                            tickFormatter={(v: number) => `$${v?.toFixed(0) || 0}`}
                            width={58}
                          />
                          <Tooltip content={<CustomTooltip />} />
                          {data.technical_analysis?.support && (
                            <ReferenceLine
                              y={data.technical_analysis.support}
                              stroke="#f59e0b" strokeDasharray="4 5" strokeOpacity={0.55}
                              label={{ value: 'S', fill: '#f59e0b', fontSize: 9, fontFamily: "'JetBrains Mono', monospace", position: 'insideBottomLeft' }}
                            />
                          )}
                          {data.technical_analysis?.resistance && (
                            <ReferenceLine
                              y={data.technical_analysis.resistance}
                              stroke="#f43f5e" strokeDasharray="4 5" strokeOpacity={0.55}
                              label={{ value: 'R', fill: '#f43f5e', fontSize: 9, fontFamily: "'JetBrains Mono', monospace", position: 'insideTopLeft' }}
                            />
                          )}
                          <Area
                            type="monotone" dataKey="price"
                            stroke="#00d975" strokeWidth={2}
                            fill="url(#priceGrad)" dot={false}
                            activeDot={{ r: 4, fill: '#00d975', stroke: 'var(--void)', strokeWidth: 2 }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </motion.div>

                  {(data.company_profile || (data.financial_records && data.financial_records.length > 0)) && (
                    <motion.div variants={fadeUp} className="void-card">
                      <SectionHeader icon={<Building2 size={14} />} label="COMPANY OVERVIEW & FINANCIALS" />

                      {data.company_profile && (
                        <>
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                            gap: 8, marginBottom: 16,
                          }}>
                            {[
                              { label: 'SECTOR', value: data.company_profile.sector },
                              { label: 'INDUSTRY', value: data.company_profile.industry },
                              { label: 'EMPLOYEES', value: data.company_profile.full_time_employees?.toLocaleString() },
                              {
                                label: 'HQ',
                                value: data.company_profile.city
                                  ? `${data.company_profile.city}, ${data.company_profile.country}`
                                  : data.company_profile.country,
                              },
                            ].filter((i) => i.value).map((item) => (
                              <DataCell key={item.label} label={item.label} value={item.value} />
                            ))}
                          </div>

                          {data.company_profile.business_summary && (
                            <div style={{
                              background: 'var(--surface)',
                              border: '1px solid var(--border)',
                              borderRadius: 10, padding: '14px 16px',
                              fontFamily: "'Inter', sans-serif",
                              fontSize: 13, lineHeight: 1.75, color: 'var(--text-secondary)',
                              marginBottom: 14,
                            }}>
                              {data.company_profile.business_summary}
                            </div>
                          )}

                          {data.company_profile.website && (
                            <a
                              href={data.company_profile.website}
                              target="_blank" rel="noopener noreferrer"
                              style={{
                                display: 'inline-flex', alignItems: 'center', gap: 5,
                                fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                                color: 'var(--info)', textDecoration: 'none',
                                marginBottom: 20, letterSpacing: '0.05em',
                              }}
                            >
                              <ExternalLink size={11} />
                              {data.company_profile.website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}
                            </a>
                          )}
                        </>
                      )}

                      {data.financial_records && data.financial_records.length > 0 && (
                        <>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                            <FileText size={12} style={{ color: 'var(--text-muted)' }} />
                            <span className="section-label">SEC FINANCIAL RECORDS</span>
                            {data.financial_records[0]?.source && (
                              <span style={{
                                fontFamily: "'JetBrains Mono', monospace",
                                fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em',
                              }}>
                                ({data.financial_records[0].source})
                              </span>
                            )}
                          </div>

                          <div style={{ overflowX: 'auto' }}>
                            <table className="fin-table">
                              <thead>
                                <tr>
                                  {['PERIOD', 'REVENUE', 'NET INCOME', 'GROSS PROFIT', 'TOTAL ASSETS', 'TOTAL DEBT', 'CASH FLOW']
                                    .map((h) => <th key={h}>{h}</th>)}
                                </tr>
                              </thead>
                              <tbody>
                                {data.financial_records.map((rec) => (
                                  <tr key={rec.period}>
                                    <td>{rec.period}</td>
                                    {[rec.revenue, rec.net_income, rec.gross_profit,
                                      rec.total_assets, rec.total_debt, rec.operating_cash_flow
                                    ].map((v, i) => (
                                      <td key={i}>{formatLargeNumber(v)}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </>
                      )}
                    </motion.div>
                  )}

                  <motion.div
                    variants={fadeUp}
                    style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}
                  >
                    <div className="void-card">
                      <SectionHeader icon={<BarChart4 size={14} />} label="TECHNICAL ANALYSIS" />
                      <div>
                        <MetricRow label="TREND" value={data.technical_analysis?.trend} />
                        <MetricRow label="MOMENTUM" value={data.technical_analysis?.momentum} />
                        <MetricRow label="VOLATILITY" value={formatNum(data.technical_analysis?.volatility)} />
                        <MetricRow
                          label="SUPPORT"
                          value={`$${formatNum(data.technical_analysis?.support)}`}
                          color="#f59e0b"
                        />
                        <MetricRow
                          label="RESISTANCE"
                          value={`$${formatNum(data.technical_analysis?.resistance)}`}
                          color="#f43f5e"
                        />
                      </div>

                      {data.technical_indicators && (
                        <>
                          <div style={{ borderTop: '1px solid var(--border)', margin: '14px 0 12px' }} />
                          <div className="section-label" style={{ marginBottom: 10 }}>LIVE INDICATORS</div>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 12px' }}>
                            {[
                              { label: 'SMA-20', value: data.technical_indicators.sma_20 ? `$${formatNum(data.technical_indicators.sma_20)}` : '—', sub: data.technical_indicators.price_vs_sma20 },
                              { label: 'SMA-50', value: data.technical_indicators.sma_50 ? `$${formatNum(data.technical_indicators.sma_50)}` : '—', sub: data.technical_indicators.price_vs_sma50 },
                              { label: 'MACD', value: data.technical_indicators.macd_line ? formatNum(data.technical_indicators.macd_line, 3) : '—', sub: data.technical_indicators.macd_crossover },
                              { label: 'BB POS', value: data.technical_indicators.bb_position !== undefined ? `${Math.max(0, (data.technical_indicators.bb_position * 100)).toFixed(0)}%` : '—', sub: data.technical_indicators.bb_position !== undefined && data.technical_indicators.bb_position < 0 ? 'BELOW BAND' : undefined },
                            ].map((ind) => (
                              <div key={ind.label} style={{
                                background: 'var(--surface)', borderRadius: 8,
                                padding: '7px 10px',
                              }}>
                                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: '0.14em', color: 'var(--text-muted)', marginBottom: 3 }}>{ind.label}</div>
                                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>{ind.value}</div>
                                {ind.sub && <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: ind.sub === 'Bullish' || ind.sub === 'above' ? 'var(--gain)' : ind.sub === 'Bearish' || ind.sub === 'below' ? 'var(--loss)' : 'var(--text-muted)', marginTop: 2, letterSpacing: '0.1em' }}>{ind.sub.toUpperCase()}</div>}
                              </div>
                            ))}
                          </div>

                          {data.technical_indicators.rsi_14 !== undefined && (
                            <div style={{ marginTop: 12 }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
                                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: '0.14em', color: 'var(--text-muted)' }}>RSI-14</span>
                                <span style={{
                                  fontFamily: "'JetBrains Mono', monospace", fontSize: 11, fontWeight: 700,
                                  color: (data.technical_indicators.rsi_14 ?? 50) >= 70 ? 'var(--loss)' : (data.technical_indicators.rsi_14 ?? 50) <= 30 ? 'var(--gain)' : 'var(--accent)',
                                }}>
                                  {formatNum(data.technical_indicators.rsi_14, 1)} · {data.technical_indicators.rsi_signal}
                                </span>
                              </div>
                              <div style={{ height: 6, background: 'var(--surface)', borderRadius: 3, overflow: 'hidden' }}>
                                <div style={{
                                  height: '100%',
                                  width: `${Math.min(100, data.technical_indicators.rsi_14 ?? 50)}%`,
                                  background: (data.technical_indicators.rsi_14 ?? 50) >= 70
                                    ? 'linear-gradient(90deg, #f59e0b, #f43f5e)'
                                    : (data.technical_indicators.rsi_14 ?? 50) <= 30
                                    ? 'linear-gradient(90deg, #00d975, #38bdf8)'
                                    : 'linear-gradient(90deg, var(--accent), #38bdf8)',
                                  borderRadius: 3,
                                  transition: 'width 0.6s ease',
                                }} />
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3 }}>
                                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: 'var(--gain)' }}>OVERSOLD 30</span>
                                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: 'var(--loss)' }}>70 OVERBOUGHT</span>
                              </div>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    <div className="void-card">
                      <SectionHeader icon={<Target size={14} />} label="RISK / CONVICTION" />
                      <div>
                        <MetricRow
                          label="RECOMMENDATION"
                          value={data.recommendation}
                          color="var(--accent)"
                        />
                        <MetricRow label="RISK LEVEL" value={data.risk_level} />
                        <MetricRow
                          label="CONFIDENCE"
                          value={`${animatedConfidence}%`}
                        />
                        <MetricRow label="HORIZON" value={data.time_horizon} />
                      </div>
                    </div>
                  </motion.div>

                  <motion.div variants={fadeUp} className="void-card">
                    <SectionHeader icon={<Newspaper size={14} />} label="NEWS FEED" />

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {(data.news_summary || []).slice(0, 5).map((article, idx) => (
                        <NewsCard key={`${article.title}-${idx}`} article={article} />
                      ))}

                      {(!data.news_summary || data.news_summary.length === 0) && (
                        <EmptyState title="NO NEWS ITEMS FOR THIS TICKER" icon="news" />
                      )}
                    </div>
                  </motion.div>

                  <motion.div variants={fadeUp} className="void-card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
                      <SectionHeader icon={<Info size={14} />} label="VERDICT" />
                      {data.data_quality && (
                        <div style={{
                          display: 'inline-flex', alignItems: 'center', gap: 6,
                          padding: '4px 10px', borderRadius: 20,
                          border: `1px solid ${
                            data.data_quality.level === 'Very High' || data.data_quality.level === 'High'
                              ? 'rgba(0,217,117,0.3)'
                              : data.data_quality.level === 'Medium'
                              ? 'rgba(245,158,11,0.3)'
                              : 'rgba(244,63,94,0.3)'
                          }`,
                          background:
                            data.data_quality.level === 'Very High' || data.data_quality.level === 'High'
                              ? 'rgba(0,217,117,0.06)'
                              : data.data_quality.level === 'Medium'
                              ? 'rgba(245,158,11,0.06)'
                              : 'rgba(244,63,94,0.06)',
                        }}>
                          <span style={{
                            width: 5, height: 5, borderRadius: '50%',
                            background:
                              data.data_quality.level === 'Very High' || data.data_quality.level === 'High'
                                ? 'var(--gain)'
                                : data.data_quality.level === 'Medium'
                                ? '#f59e0b'
                                : 'var(--loss)',
                            display: 'inline-block',
                          }} />
                          <span style={{
                            fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                            letterSpacing: '0.14em',
                            color:
                              data.data_quality.level === 'Very High' || data.data_quality.level === 'High'
                                ? 'var(--gain)'
                                : data.data_quality.level === 'Medium'
                                ? '#f59e0b'
                                : 'var(--loss)',
                          }}>
                            {data.data_quality.label?.toUpperCase()}
                          </span>
                        </div>
                      )}
                    </div>
                    <p style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: 14, lineHeight: 1.85, color: 'var(--text-secondary)', margin: 0,
                    }}>
                      {data.verdict || 'No verdict returned.'}
                    </p>
                    {data.quantitative_summary && (
                      <div style={{
                        marginTop: 16,
                        background: 'rgba(56,189,248,0.04)',
                        border: '1px solid rgba(56,189,248,0.14)',
                        borderLeft: '3px solid rgba(56,189,248,0.4)',
                        borderRadius: 10, padding: '12px 16px',
                        fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 12, color: 'var(--info)', lineHeight: 1.75,
                        letterSpacing: '0.03em',
                      }}>
                        {data.quantitative_summary}
                      </div>
                    )}
                  </motion.div>
                </div>

                <div
                  className="sidebar-sticky"
                  style={{
                    display: 'flex', flexDirection: 'column', gap: 16,
                    position: 'sticky', top: 24,
                  }}
                >
                  <motion.div variants={fadeUp} className="void-card">
                    <div className="section-label" style={{ marginBottom: 12 }}>TARGET PRICE</div>
                    <div style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 40, fontWeight: 700, color: 'var(--accent)',
                      lineHeight: 1,
                      textShadow: '0 0 40px var(--accent-glow)',
                    }}>
                      ${animatedTarget}
                    </div>

                    <div style={{ marginTop: 20 }}>
                      {[
                        { label: '3M TARGET', value: data.target_prices?.three_months?.price },
                        { label: '6M TARGET', value: data.target_prices?.six_months?.price },
                        { label: '12M TARGET', value: data.target_prices?.twelve_months?.price },
                      ].map((tp) => (
                        <MetricRow key={tp.label} label={tp.label} value={`$${formatNum(tp.value)}`} decimals={2} />
                      ))}
                    </div>
                  </motion.div>

                  {data.analyst_consensus?.mean_target && (
                    <motion.div variants={fadeUp} className="void-card">
                      <div className="section-label" style={{ marginBottom: 12 }}>ANALYST CONSENSUS</div>
                      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 28, fontWeight: 700, color: 'var(--info)' }}>
                          ${formatNum(data.analyst_consensus.mean_target)}
                        </span>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: 'var(--text-muted)', letterSpacing: '0.1em' }}>MEAN TARGET</span>
                      </div>
                      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: data.analyst_consensus.recommendation_key === 'buy' || data.analyst_consensus.recommendation_key === 'strong_buy' ? 'var(--gain)' : data.analyst_consensus.recommendation_key === 'sell' || data.analyst_consensus.recommendation_key === 'strong_sell' ? 'var(--loss)' : 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 14, textTransform: 'uppercase' }}>
                        {data.analyst_consensus.recommendation_key?.replace('_', ' ')} · {data.analyst_consensus.num_analysts} analysts
                      </div>
                      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
                        {[
                          { label: 'HIGH', value: data.analyst_consensus.high_target, color: 'var(--gain)' },
                          { label: 'LOW', value: data.analyst_consensus.low_target, color: 'var(--loss)' },
                        ].map((tp) => tp.value ? (
                          <div key={tp.label} style={{ flex: 1, background: 'var(--surface)', borderRadius: 8, padding: '7px 10px', textAlign: 'center' }}>
                            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, letterSpacing: '0.14em', color: 'var(--text-muted)', marginBottom: 3 }}>{tp.label}</div>
                            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, fontWeight: 700, color: tp.color }}>${formatNum(tp.value)}</div>
                          </div>
                        ) : null)}
                      </div>
                      {(data.analyst_consensus.strong_buy !== undefined || data.analyst_consensus.buy !== undefined) && (() => {
                        const sb = data.analyst_consensus.strong_buy ?? 0;
                        const b = data.analyst_consensus.buy ?? 0;
                        const h = data.analyst_consensus.hold ?? 0;
                        const s = data.analyst_consensus.sell ?? 0;
                        const ss = data.analyst_consensus.strong_sell ?? 0;
                        const total = sb + b + h + s + ss;
                        if (total === 0) return null;
                        return (
                          <div>
                            <div style={{ height: 8, borderRadius: 4, overflow: 'hidden', display: 'flex', gap: 1 }}>
                              {[{ v: sb + b, c: 'var(--gain)' }, { v: h, c: '#f59e0b' }, { v: s + ss, c: 'var(--loss)' }].map((seg, i) => (
                                <div key={i} style={{ flex: seg.v, background: seg.c, transition: 'flex 0.5s ease' }} />
                              ))}
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 5 }}>
                              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: 'var(--gain)' }}>BUY {sb + b}</span>
                              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: '#f59e0b' }}>HOLD {h}</span>
                              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 8, color: 'var(--loss)' }}>SELL {s + ss}</span>
                            </div>
                          </div>
                        );
                      })()}
                    </motion.div>
                  )}

                  <motion.div variants={fadeUp} className="void-card">
                    <SectionHeader label="KEY METRICS" />
                    <div>
                      <MetricRow label="MARKET CAP" value={data.key_metrics?.market_cap} />
                      <MetricRow label="P/E (TTM)" value={formatNum(data.key_metrics?.pe_ratio)} />
                      <MetricRow label="P/E (FWD)" value={formatNum(data.key_metrics?.forward_pe)} />
                      <MetricRow label="P/B RATIO" value={formatNum(data.key_metrics?.price_to_book)} />
                      <MetricRow label="EPS (TTM)" value={data.key_metrics?.eps_trailing ? `$${formatNum(data.key_metrics.eps_trailing)}` : undefined} />
                      <MetricRow label="BETA" value={formatNum(data.key_metrics?.beta)} />
                      <MetricRow label="DIV YIELD" value={data.key_metrics?.dividend_yield ? `${formatNum(data.key_metrics.dividend_yield)}%` : undefined} />
                      <MetricRow label="52W HIGH" value={`$${formatNum(data.key_metrics?.fifty_two_week_high)}`} />
                      <MetricRow label="52W LOW" value={`$${formatNum(data.key_metrics?.fifty_two_week_low)}`} />
                      <MetricRow label="VOLUME" value={data.key_metrics?.volume?.toLocaleString()} />
                      {data.key_metrics?.revenue_growth !== undefined && data.key_metrics.revenue_growth !== null && (
                        <MetricRow label="REV GROWTH" value={`${(data.key_metrics.revenue_growth * 100).toFixed(1)}%`} color={data.key_metrics.revenue_growth >= 0 ? 'var(--gain)' : 'var(--loss)'} />
                      )}
                      {data.key_metrics?.profit_margins !== undefined && data.key_metrics.profit_margins !== null && (
                        <MetricRow label="NET MARGIN" value={`${(data.key_metrics.profit_margins * 100).toFixed(1)}%`} />
                      )}
                      {data.key_metrics?.return_on_equity !== undefined && data.key_metrics.return_on_equity !== null && (
                        <MetricRow label="ROE" value={`${(data.key_metrics.return_on_equity * 100).toFixed(1)}%`} />
                      )}
                      {data.key_metrics?.debt_to_equity !== undefined && data.key_metrics.debt_to_equity !== null && (
                        <MetricRow label="D/E RATIO" value={`${formatNum(data.key_metrics.debt_to_equity)}%`} color={data.key_metrics.debt_to_equity > 200 ? 'var(--loss)' : undefined} />
                      )}
                    </div>
                  </motion.div>

                  <motion.div variants={fadeUp} className="void-card">
                    <SectionHeader icon={<ShieldAlert size={14} />} label="AI REASONING" />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {(data.reasoning || []).map((point, idx) => (
                        <ReasoningItem key={idx} index={idx} text={point} />
                      ))}
                      {(!data.reasoning || data.reasoning.length === 0) && (
                        <EmptyState title="NO REASONING RETURNED" icon="data" />
                      )}
                    </div>
                  </motion.div>
                </div>
              </motion.div>
            )}

            <div className="status-bar">
              <span>SYS::ONLINE</span>
              <span style={{ color: 'var(--accent)' }}>● READY</span>
              <span>v2.0.0</span>
            </div>
          </div>
        )}
      </div>
    );
  }