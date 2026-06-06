import React, { useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  Search, TrendingUp, TrendingDown, Newspaper, ShieldAlert,
  BarChart4, CheckCircle2, Activity, Target, Info, Building2,
  FileText, ExternalLink, Users, Globe, Database, Zap,
} from 'lucide-react';

const API_BASE = "http://localhost:8000/api";

type ViewState = 'landing' | 'select' | 'dashboard';
type PhaseStatus = 'idle' | 'running' | 'done';

type NewsArticle = { title: string; source: string; date: string; sentiment: string; summary: string; url?: string; };
type TargetPoint = { price?: number; rationale?: string; };
type CompanyProfile = { business_summary?: string; sector?: string; industry?: string; full_time_employees?: number; country?: string; city?: string; website?: string; };
type FinancialRecord = { period: string; revenue?: number; net_income?: number; gross_profit?: number; total_assets?: number; total_debt?: number; operating_cash_flow?: number; source?: string; };

type FinalData = {
  ticker: string; company_name?: string; current_price?: number; day_change_pct?: number;
  volatility?: number; recommendation?: string; verdict?: string; quantitative_summary?: string;
  time_horizon?: string; confidence_score?: number; risk_level?: string;
  key_metrics?: { market_cap?: string; pe_ratio?: number; beta?: number; dividend_yield?: number; fifty_two_week_high?: number; fifty_two_week_low?: number; volume?: number; };
  company_profile?: CompanyProfile; financial_records?: FinancialRecord[];
  technical_analysis?: { trend?: string; volatility?: number; support?: number; resistance?: number; };
  target_price?: number; target_prices?: { three_months?: TargetPoint; six_months?: TargetPoint; twelve_months?: TargetPoint; };
  news_summary?: NewsArticle[]; reasoning?: string[];
};

const SENTIMENT_COLORS: Record<string, string> = {
  Bullish: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10',
  Bearish: 'text-red-400 border-red-500/30 bg-red-500/10',
  Neutral: 'text-slate-400 border-slate-700 bg-slate-800/50',
};

function formatLargeNumber(val: number | null | undefined): string {
  if (val === null || val === undefined) return 'N/A';
  if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
  return `$${val.toFixed(0)}`;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-900/95 px-4 py-3 shadow-xl backdrop-blur-sm">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-lg font-bold text-emerald-400">${Number(payload[0].value).toFixed(2)}</div>
    </div>
  );
}

const PIPE_NODES = [
  { id: 'prefetch', label: 'Prefetch Data', icon: Database, cx: 300, cy: 40 },
  { id: 'data', label: 'Market Data', icon: BarChart4, cx: 110, cy: 135 },
  { id: 'news', label: 'News Analysis', icon: Newspaper, cx: 300, cy: 135 },
  { id: 'analysis', label: 'Technicals', icon: Activity, cx: 490, cy: 135 },
  { id: 'risk', label: 'Risk Officer', icon: ShieldAlert, cx: 300, cy: 230 },
  { id: 'expert', label: 'Equity Expert', icon: Target, cx: 300, cy: 320 },
  { id: 'complete', label: 'Assemble', icon: CheckCircle2, cx: 300, cy: 400 },
];

const PIPE_EDGES = [
  { from: 'prefetch', to: 'data' }, { from: 'prefetch', to: 'news' }, { from: 'prefetch', to: 'analysis' },
  { from: 'data', to: 'risk' }, { from: 'news', to: 'risk' }, { from: 'analysis', to: 'risk' },
  { from: 'risk', to: 'expert' }, { from: 'expert', to: 'complete' },
];

const NODE_W = 140, NODE_H = 50, NODE_R = 14;

function edgePath(from: typeof PIPE_NODES[0], to: typeof PIPE_NODES[0]): string {
  const x1 = from.cx, y1 = from.cy + NODE_H / 2;
  const x2 = to.cx, y2 = to.cy - NODE_H / 2;
  if (x1 === x2) return `M ${x1} ${y1} L ${x2} ${y2}`;
  const midY = (y1 + y2) / 2;
  return `M ${x1} ${y1} C ${x1} ${midY}, ${x2} ${midY}, ${x2} ${y2}`;
}

function WorkflowPipeline({ phases }: { phases: Record<string, PhaseStatus> }) {
  const nodeMap = new Map(PIPE_NODES.map(n => [n.id, n]));

  return (
    <div className="mx-auto max-w-xl py-4">
      <svg viewBox="0 0 600 430" className="w-full">
        {PIPE_EDGES.map((e, i) => {
          const fromNode = nodeMap.get(e.from)!;
          const toNode = nodeMap.get(e.to)!;
          const fromS = phases[e.from] || 'idle';
          const toS = phases[e.to] || 'idle';
          const active = fromS === 'done' || fromS === 'running';
          const flowing = fromS === 'done' && toS === 'running';
          const d = edgePath(fromNode, toNode);

          return flowing ? (
            <motion.path key={`e${i}`} d={d} fill="none" stroke="#22c55e" strokeWidth={2}
              strokeDasharray="8 4" opacity={0.9}
              animate={{ strokeDashoffset: [0, -24] }}
              transition={{ repeat: Infinity, duration: 0.8, ease: 'linear' }} />
          ) : active ? (
            <path key={`e${i}`} d={d} fill="none" stroke="#22c55e" strokeWidth={1.5}
              strokeDasharray="none" opacity={0.7} />
          ) : (
            <path key={`e${i}`} d={d} fill="none" stroke="#1e293b" strokeWidth={1.5}
              strokeDasharray="4 4" opacity={0.4} />
          );
        })}

        {PIPE_NODES.map(node => {
          const status = phases[node.id] || 'idle';
          const x = node.cx - NODE_W / 2, y = node.cy - NODE_H / 2;
          const isRunning = status === 'running';
          const isDone = status === 'done';

          const fillColor = isRunning ? '#05140d' : isDone ? '#061a0e' : '#0c1220';
          const strokeColor = isRunning ? '#22c55e' : isDone ? '#16a34a' : '#1e293b';
          const textColor = isRunning ? '#22c55e' : isDone ? '#86efac' : '#475569';

          return (
            <g key={node.id}>
              {isRunning ? (
                <motion.rect
                  x={x} y={y} width={NODE_W} height={NODE_H} rx={NODE_R}
                  fill={fillColor} stroke={strokeColor} strokeWidth={2.5}
                  animate={{
                    stroke: ['#22c55e', '#4ade80', '#22c55e'],
                  }}
                  transition={{ repeat: Infinity, duration: 1, ease: 'easeInOut' }} />
              ) : (
                <rect x={x} y={y} width={NODE_W} height={NODE_H} rx={NODE_R}
                  fill={fillColor} stroke={strokeColor} strokeWidth={1.5} />
              )}
              <text x={node.cx} y={node.cy + 2} textAnchor="middle" dominantBaseline="middle"
                fill={textColor} fontSize={12.5} fontWeight={isRunning ? 700 : isDone ? 600 : 400}
                fontFamily="system-ui, sans-serif">
                {node.label}
              </text>
              {isDone && (
                <text x={x + NODE_W - 16} y={y + 14} fill="#22c55e" fontSize={18}
                  fontFamily="system-ui, sans-serif" fontWeight={700}>✓</text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default function App() {
  const [view, setView] = useState<ViewState>('landing');
  const [query, setQuery] = useState('');
  const [tickers, setTickers] = useState<string[]>([]);
  const [selectedTicker, setSelectedTicker] = useState('');
  const [data, setData] = useState<FinalData | null>(null);
  const [history, setHistory] = useState<{ date: string; price: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [error, setError] = useState<string>('');
  const [activePhases, setActivePhases] = useState<Record<string, PhaseStatus>>({
    prefetch: 'idle', data: 'idle', news: 'idle', analysis: 'idle',
    risk: 'idle', expert: 'idle', complete: 'idle',
  });
  const dataReceivedRef = useRef(false);

  useEffect(() => {
    axios.get(`${API_BASE}/tickers/search`).then((res) => setTickers(res.data)).catch(() => setTickers(['AAPL', 'NVDA', 'TSLA']));
  }, []);

  const filteredTickers = useMemo(() => {
    const q = query.trim().toUpperCase();
    return q ? tickers.filter((t) => t.includes(q)) : tickers;
  }, [query, tickers]);

  const MAX_VISIBLE = 120;
  const visibleTickers = filteredTickers.slice(0, MAX_VISIBLE);

  const formatNum = (val: unknown, decimals = 2) => {
    if (val === null || val === undefined || Number.isNaN(Number(val))) return 'N/A';
    return Number(val).toFixed(decimals);
  };

  const handleSelectTicker = async (symbol: string) => {
    setSelectedTicker(symbol);
    setView('dashboard');
    setLoading(true);
    setError('');
    setData(null);
    setLogs([]);
    setActivePhases({ prefetch: 'idle', data: 'idle', news: 'idle', analysis: 'idle', risk: 'idle', expert: 'idle', complete: 'idle' });
    dataReceivedRef.current = false;

    try {
      const histRes = await axios.get(`${API_BASE}/stock/${symbol}/history`);
      setHistory(histRes.data.history || []);

      const es = new EventSource(`${API_BASE}/analyze/stream/${symbol}`);

      es.addEventListener('log', (e: MessageEvent) => {
        setLogs((prev) => [...prev.slice(-12), String(e.data)]);
      });

      es.addEventListener('phase', (e: MessageEvent) => {
        try {
          const payload = JSON.parse(String(e.data));
          setActivePhases((prev) => ({ ...prev, [payload.step]: payload.status === 'done' ? 'done' : 'running' }));
        } catch {}
      });

      es.addEventListener('final_result', (e: MessageEvent) => {
        try {
          dataReceivedRef.current = true;
          setData(JSON.parse(String(e.data)));
          setActivePhases((prev) => ({ ...prev, complete: 'done' }));
        } catch {
          setError('The server returned data that could not be parsed as JSON.');
        } finally {
          setLoading(false);
          es.close();
        }
      });

      es.onerror = () => {
        setLoading(false);
        es.close();
        if (!dataReceivedRef.current) {
          setError('Stream closed before a final result was returned.');
        }
      };
    } catch (err: any) {
      setLoading(false);
      setError(err?.response?.data?.detail || err?.message || 'Failed to load ticker data.');
    }
  };

  const minPrice = history.length ? Math.min(...history.map((h) => h.price)) : 0;
  const maxPrice = history.length ? Math.max(...history.map((h) => h.price)) : 0;

  return (
    <div className="min-h-screen bg-[#05070a] text-slate-100">
      {view === 'landing' && (
        <div className="flex min-h-screen flex-col items-center justify-center px-6">
          <div className="max-w-2xl text-center">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
              <Activity size={16} /> Financial intelligence dashboard
            </div>
            <h1 className="mb-5 text-5xl font-black tracking-tight md:text-7xl">STOCK INTELLIGENCE</h1>
            <p className="mx-auto mb-8 max-w-xl text-slate-400">
              Streamed market data, technical analysis, news sentiment, and a final investment verdict in one view.
            </p>
            <button onClick={() => setView('select')} className="rounded-full bg-emerald-500 px-8 py-3 font-bold text-black transition hover:bg-emerald-400">
              Access System
            </button>
          </div>
        </div>
      )}

      {view === 'select' && (
        <div className="mx-auto max-w-4xl px-6 py-10">
          <div className="mb-6 flex items-center justify-between gap-4">
            <button onClick={() => setView('landing')} className="rounded-full border border-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-600">Back</button>
            <div className="text-sm text-slate-500">Choose a ticker to start analysis</div>
          </div>
          <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6 shadow-2xl shadow-black/20">
            <div className="mb-4 flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950 px-4 py-3">
              <Search size={18} className="text-slate-500" />
              <input className="w-full bg-transparent text-slate-100 outline-none placeholder:text-slate-500" placeholder="Search ticker symbol..." value={query} onChange={(e) => setQuery(e.target.value)} />
            </div>
            <div className="mb-2 text-xs text-slate-500">
              {filteredTickers.length > MAX_VISIBLE ? `Showing ${MAX_VISIBLE} of ${filteredTickers.length} tickers — type to narrow results` : `${filteredTickers.length} tickers available`}
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              {visibleTickers.map((symbol) => (
                <button key={symbol} onClick={() => handleSelectTicker(symbol)} className="rounded-2xl border border-slate-800 bg-slate-950 px-4 py-5 text-left transition hover:-translate-y-0.5 hover:border-emerald-500/40 hover:bg-slate-900">
                  <div className="text-lg font-bold">{symbol}</div>
                  <div className="text-xs text-slate-500">Run analysis</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {view === 'dashboard' && (
        <div className="mx-auto max-w-7xl px-6 py-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <button onClick={() => { setView('select'); setData(null); setError(''); setLogs([]); }} className="rounded-full border border-slate-800 px-4 py-2 text-sm text-slate-300 transition hover:border-slate-600">Change ticker</button>
            <div className="text-sm text-slate-500">{selectedTicker ? `Analyzing ${selectedTicker}` : 'No ticker selected'}</div>
          </div>

          {loading && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
              <div className="mb-4 flex items-center gap-2">
                <Zap size={18} className="text-emerald-400" />
                <span className="text-lg font-bold">Agent pipeline</span>
                <span className="text-xs text-slate-500 ml-2">{selectedTicker}</span>
              </div>
              <WorkflowPipeline phases={activePhases} />
              {logs.length > 0 && (
                <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950 p-4 max-h-32 overflow-auto">
                  <div className="text-xs text-slate-500 mb-2">Live feed</div>
                  {logs.slice(-6).map((line, idx) => (
                    <div key={idx} className="text-xs text-slate-400 py-0.5">{line}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="mb-6 rounded-3xl border border-red-900/50 bg-red-950/20 p-5 text-red-200">{error}</div>
          )}

          {data && (
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
              <div className="space-y-8 lg:col-span-2">
                <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                  <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
                    <div>
                      <div className="text-sm uppercase tracking-widest text-slate-500">Equity dossier</div>
                      <h2 className="mt-1 text-3xl font-black">{data.ticker} {data.company_name ? `- ${data.company_name}` : ''}</h2>
                      {data.company_profile?.sector && (<div className="mt-1 text-xs text-slate-500">{data.company_profile.industry || data.company_profile.sector}</div>)}
                    </div>
                    <div className="rounded-2xl border border-slate-800 bg-slate-950 px-5 py-3">
                      <div className="text-xs uppercase text-slate-500">Current price</div>
                      <div className="text-2xl font-bold">${formatNum(data.current_price)}</div>
                      <div className={`text-sm flex items-center gap-1 ${Number(data.day_change_pct || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {Number(data.day_change_pct || 0) >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        {formatNum(data.day_change_pct)}%
                      </div>
                    </div>
                  </div>
                  <div className="h-[340px] mt-2">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={history} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                        <defs>
                          <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#22c55e" stopOpacity={0.35} />
                            <stop offset="50%" stopColor="#22c55e" stopOpacity={0.12} />
                            <stop offset="100%" stopColor="#22c55e" stopOpacity={0.02} />
                          </linearGradient>
                          <linearGradient id="strokeGradient" x1="0" y1="0" x2="1" y2="0">
                            <stop offset="0%" stopColor="#16a34a" /><stop offset="100%" stopColor="#22c55e" />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" strokeOpacity={0.6} />
                        <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 11 }} tickLine={{ stroke: '#334155' }} axisLine={{ stroke: '#334155' }} tickFormatter={(v: string) => v.slice(5)} />
                        <YAxis tick={{ fill: '#64748b', fontSize: 11 }} tickLine={{ stroke: '#334155' }} axisLine={{ stroke: '#334155' }} domain={[minPrice * 0.98, maxPrice * 1.02]} tickFormatter={(v: number) => `$${v.toFixed(0)}`} />
                        <Tooltip content={<CustomTooltip />} />
                        {data.technical_analysis?.support && (<ReferenceLine y={data.technical_analysis.support} stroke="#f59e0b" strokeDasharray="6 3" strokeOpacity={0.6} label={{ value: 'Support', fill: '#f59e0b', fontSize: 10, position: 'insideBottomLeft' }} />)}
                        {data.technical_analysis?.resistance && (<ReferenceLine y={data.technical_analysis.resistance} stroke="#ef4444" strokeDasharray="6 3" strokeOpacity={0.6} label={{ value: 'Resistance', fill: '#ef4444', fontSize: 10, position: 'insideTopLeft' }} />)}
                        <Area type="monotone" dataKey="price" stroke="url(#strokeGradient)" strokeWidth={2.5} fill="url(#priceGradient)" dot={false} activeDot={{ r: 5, fill: '#22c55e', stroke: '#05070a', strokeWidth: 2 }} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {(data.company_profile || (data.financial_records && data.financial_records.length > 0)) && (
                  <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-bold"><Building2 size={18} />Company overview &amp; financials</div>
                    {data.company_profile && (
                      <>
                        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 text-sm">
                          {data.company_profile.sector && (<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="text-xs text-slate-500">Sector</div><div className="font-semibold">{data.company_profile.sector}</div></div>)}
                          {data.company_profile.industry && (<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="text-xs text-slate-500">Industry</div><div className="font-semibold">{data.company_profile.industry}</div></div>)}
                          {data.company_profile.full_time_employees && (<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="flex items-center gap-1 text-xs text-slate-500"><Users size={12} /> Employees</div><div className="font-semibold">{data.company_profile.full_time_employees.toLocaleString()}</div></div>)}
                          {data.company_profile.country && (<div className="rounded-2xl border border-slate-800 bg-slate-950 p-3"><div className="flex items-center gap-1 text-xs text-slate-500"><Globe size={12} /> HQ</div><div className="font-semibold">{data.company_profile.city ? `${data.company_profile.city}, ` : ''}{data.company_profile.country}</div></div>)}
                        </div>
                        {data.company_profile.business_summary && (<div className="mb-6 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">{data.company_profile.business_summary}</div>)}
                        {data.company_profile.website && (<a href={data.company_profile.website} target="_blank" rel="noopener noreferrer" className="mb-4 inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition"><ExternalLink size={12} />{data.company_profile.website.replace(/^https?:\/\/(www\.)?/, '').split('/')[0]}</a>)}
                      </>
                    )}
                    {data.financial_records && data.financial_records.length > 0 && (
                      <>
                        <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-400"><FileText size={14} />SEC financial records{data.financial_records[0]?.source && (<span className="text-xs text-slate-600">({data.financial_records[0].source})</span>)}</div>
                        <div className="overflow-x-auto">
                          <table className="w-full text-sm">
                            <thead><tr className="border-b border-slate-800">
                              <th className="pb-2 pr-4 text-left text-xs text-slate-500">Period</th>
                              <th className="pb-2 pr-4 text-right text-xs text-slate-500">Revenue</th>
                              <th className="pb-2 pr-4 text-right text-xs text-slate-500">Net Income</th>
                              <th className="pb-2 pr-4 text-right text-xs text-slate-500">Gross Profit</th>
                              <th className="pb-2 pr-4 text-right text-xs text-slate-500">Total Assets</th>
                              <th className="pb-2 pr-4 text-right text-xs text-slate-500">Total Debt</th>
                              <th className="pb-2 text-right text-xs text-slate-500">Cash Flow</th>
                            </tr></thead>
                            <tbody>{data.financial_records.map((rec) => (
                              <tr key={rec.period} className="border-b border-slate-800/50">
                                <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{rec.period}</td>
                                <td className="py-2.5 pr-4 text-right font-semibold">{formatLargeNumber(rec.revenue)}</td>
                                <td className="py-2.5 pr-4 text-right font-semibold">{formatLargeNumber(rec.net_income)}</td>
                                <td className="py-2.5 pr-4 text-right font-semibold">{formatLargeNumber(rec.gross_profit)}</td>
                                <td className="py-2.5 pr-4 text-right font-semibold">{formatLargeNumber(rec.total_assets)}</td>
                                <td className="py-2.5 pr-4 text-right font-semibold">{formatLargeNumber(rec.total_debt)}</td>
                                <td className="py-2.5 text-right font-semibold">{formatLargeNumber(rec.operating_cash_flow)}</td>
                              </tr>
                            ))}</tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                  <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-bold"><BarChart4 size={18} />Technical analysis</div>
                    <div className="space-y-3 text-sm text-slate-300">
                      <div className="flex justify-between"><span>Trend</span><span className="font-semibold">{data.technical_analysis?.trend || 'N/A'}</span></div>
                      <div className="flex justify-between"><span>Volatility</span><span className="font-semibold">{formatNum(data.technical_analysis?.volatility)}</span></div>
                      <div className="flex justify-between"><span>Support</span><span className="font-semibold text-amber-400">${formatNum(data.technical_analysis?.support)}</span></div>
                      <div className="flex justify-between"><span>Resistance</span><span className="font-semibold text-red-400">${formatNum(data.technical_analysis?.resistance)}</span></div>
                    </div>
                  </div>
                  <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                    <div className="mb-4 flex items-center gap-2 text-lg font-bold"><Target size={18} />Risk / conviction</div>
                    <div className="space-y-3 text-sm text-slate-300">
                      <div className="flex justify-between"><span>Recommendation</span><span className="font-semibold text-emerald-400">{data.recommendation || 'N/A'}</span></div>
                      <div className="flex justify-between"><span>Risk level</span><span className="font-semibold">{data.risk_level || 'N/A'}</span></div>
                      <div className="flex justify-between"><span>Confidence</span><span className="font-semibold">{formatNum(data.confidence_score)}%</span></div>
                      <div className="flex justify-between"><span>Horizon</span><span className="font-semibold">{data.time_horizon || 'N/A'}</span></div>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                  <div className="mb-4 flex items-center gap-2 text-lg font-bold"><Newspaper size={18} />News summary</div>
                  <div className="space-y-4">
                    {(data.news_summary || []).slice(0, 5).map((article, idx) => (
                      <div key={`${article.title}-${idx}`} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="font-semibold text-slate-100">{article.title || 'Untitled'}</div>
                          <span className={`rounded-full border px-2 py-0.5 text-xs ${SENTIMENT_COLORS[article.sentiment] || SENTIMENT_COLORS.Neutral}`}>{article.sentiment || 'Neutral'}</span>
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-slate-500">
                          <span>{article.source || 'Unknown'}</span>
                          {article.date && <span>• {article.date}</span>}
                          {article.url && (<a href={article.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-blue-400 hover:text-blue-300"><ExternalLink size={10} />link</a>)}
                        </div>
                        <p className="mt-3 text-sm leading-5 text-slate-300">{article.summary || 'No summary available.'}</p>
                      </div>
                    ))}
                    {(!data.news_summary || data.news_summary.length === 0) && (<div className="text-sm text-slate-500">No news items returned for this ticker.</div>)}
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                  <div className="mb-4 flex items-center gap-2 text-lg font-bold"><Info size={18} />Verdict</div>
                  <p className="leading-7 text-slate-300">{data.verdict || 'No verdict returned.'}</p>
                  {data.quantitative_summary && (<p className="mt-4 rounded-2xl border border-blue-900/40 bg-blue-950/20 p-4 text-sm text-blue-100">{data.quantitative_summary}</p>)}
                </div>
              </div>

              <div className="space-y-8">
                <div className="rounded-3xl border border-slate-800 bg-slate-900 p-6">
                  <div className="mb-2 text-xs uppercase tracking-widest text-slate-500">Target prices</div>
                  <div className="text-4xl font-black text-emerald-400">${formatNum(data.target_price)}</div>
                  <div className="mt-6 space-y-3 text-sm">
                    <div className="flex justify-between"><span>3M target</span><span className="font-bold">${formatNum(data.target_prices?.three_months?.price)}</span></div>
                    <div className="flex justify-between"><span>6M target</span><span className="font-bold">${formatNum(data.target_prices?.six_months?.price)}</span></div>
                    <div className="flex justify-between"><span>12M target</span><span className="font-bold">${formatNum(data.target_prices?.twelve_months?.price)}</span></div>
                  </div>
                </div>
                <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                  <div className="mb-4 text-lg font-bold">Key metrics</div>
                  <div className="space-y-3 text-sm text-slate-300">
                    <div className="flex justify-between"><span>Market cap</span><span className="font-semibold">{data.key_metrics?.market_cap || 'N/A'}</span></div>
                    <div className="flex justify-between"><span>P/E ratio</span><span className="font-semibold">{formatNum(data.key_metrics?.pe_ratio)}</span></div>
                    <div className="flex justify-between"><span>Beta</span><span className="font-semibold">{formatNum(data.key_metrics?.beta)}</span></div>
                    <div className="flex justify-between"><span>Dividend yield</span><span className="font-semibold">{formatNum(data.key_metrics?.dividend_yield)}%</span></div>
                    <div className="flex justify-between"><span>52W high</span><span className="font-semibold">${formatNum(data.key_metrics?.fifty_two_week_high)}</span></div>
                    <div className="flex justify-between"><span>52W low</span><span className="font-semibold">${formatNum(data.key_metrics?.fifty_two_week_low)}</span></div>
                    <div className="flex justify-between"><span>Volume</span><span className="font-semibold">{data.key_metrics?.volume?.toLocaleString() || 'N/A'}</span></div>
                  </div>
                </div>
                <div className="rounded-3xl border border-slate-800 bg-slate-900/50 p-6">
                  <div className="mb-4 flex items-center gap-2 text-lg font-bold"><ShieldAlert size={18} />Reasoning</div>
                  <div className="space-y-3">
                    {(data.reasoning || []).map((point, idx) => (<div key={idx} className="rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">{point}</div>))}
                    {(!data.reasoning || data.reasoning.length === 0) && (<div className="text-sm text-slate-500">No reasoning points returned.</div>)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}