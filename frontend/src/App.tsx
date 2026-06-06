import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2, 
  Newspaper, Activity, BarChart3, Clock, ShieldCheck, Loader2,
  ArrowRight, PieChart, Zap, Globe, Cpu, ChevronDown
} from 'lucide-react';

// --- Types ---
interface NewsArticle {
  title: string;
  source: string;
  date: string;
  sentiment: string;
  summary: string;
}

interface AnalysisData {
  ticker: string;
  company_name: string;
  current_price: number;
  day_change_pct: number;
  volatility: number;
  key_metrics: any;
  news_summary: NewsArticle[];
  technical_analysis: any;
  fundamental_analysis: any;
  recommendation: string;
  target_price: number;
  time_horizon: string;
  confidence_score: number;
  risk_level: string;
  verdict: string;
  reasoning: string[];
}

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [view, setView] = useState<'landing' | 'select' | 'dashboard'>('landing');
  const [ticker, setTicker] = useState('AAPL');
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalysisData | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTickers();
  }, []);

  const fetchTickers = async () => {
    try {
      const res = await axios.get(`${API_BASE}/tickers`);
      setTickers(res.data);
    } catch (err) {
      console.error("Failed to fetch tickers", err);
    }
  };

  const handleAnalyze = async (symbol: string) => {
    setTicker(symbol);
    setView('dashboard');
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const histRes = await axios.get(`${API_BASE}/stock/${symbol}/history`);
      setHistory(histRes.data);
      const res = await axios.post(`${API_BASE}/analyze`, { ticker: symbol }, { timeout: 600000 });
      setData(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "System overload. Please try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-slate-100 font-sans">
      <AnimatePresence mode="wait">
        
        {/* --- 1. LANDING PAGE --- */}
        {view === 'landing' && (
          <motion.div 
            key="landing"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, y: -50 }}
            className="flex flex-col items-center justify-center min-h-screen p-6 text-center"
          >
            <motion.div 
              initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
              className="bg-green-500/20 p-4 rounded-3xl mb-8 accent-glow"
            >
              <TrendingUp className="text-green-500 w-12 h-12" />
            </motion.div>
            <h1 className="text-6xl md:text-8xl font-black mb-6 tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-500">
              STOCK INTELLIGENCE
            </h1>
            <p className="max-w-2xl text-slate-400 text-lg md:text-xl mb-12 leading-relaxed">
              Our Multi-Agent AI Swarm analyzes thousands of data points—from real-time price action to 
              global sentiment—to provide institutional-grade investment verdicts.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mb-12 text-left">
              <FeatureCard icon={<Cpu className="text-green-400"/>} title="Neural Analysis" desc="Deep-dive into technical indicators & volatility." />
              <FeatureCard icon={<Globe className="text-blue-400"/>} title="Global Sentiment" desc="Real-time news processing from verified sources." />
              <FeatureCard icon={<Zap className="text-amber-400"/>} title="Instant Execution" desc="Synthesized investment thesis in seconds." />
            </div>
            <button 
              onClick={() => setView('select')}
              className="fin-btn flex items-center gap-3 text-lg group"
            >
              Get Started <ArrowRight className="group-hover:translate-x-1 transition-transform" />
            </button>
          </motion.div>
        )}

        {/* --- 2. TICKER SELECTION --- */}
        {view === 'select' && (
          <motion.div 
            key="select"
            initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center min-h-screen p-6"
          >
            <div className="glass-card p-10 max-w-xl w-full text-center">
              <PieChart className="text-green-500 mx-auto mb-6 w-10 h-10" />
              <h2 className="text-3xl font-bold mb-2">Identify Target</h2>
              <p className="text-slate-500 mb-8">Select a NASDAQ ticker for comprehensive analysis</p>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-8">
                {tickers.map(t => (
                  <button 
                    key={t}
                    onClick={() => handleAnalyze(t)}
                    className="p-3 rounded-xl bg-slate-800/50 border border-slate-700 hover:border-green-500/50 hover:bg-green-500/5 transition-all font-bold tracking-wider"
                  >
                    {t}
                  </button>
                ))}
              </div>
              <div className="text-xs text-slate-600 uppercase tracking-widest font-bold">
                Nasdaq Real-time Coverage Enabled
              </div>
            </div>
          </motion.div>
        )}

        {/* --- 3. MAIN DASHBOARD --- */}
        {view === 'dashboard' && (
          <motion.div 
            key="dashboard"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            className="pb-12"
          >
            <nav className="border-b border-slate-800 sticky top-0 z-50 bg-black/50 backdrop-blur-xl px-6 py-4">
              <div className="max-w-[1400px] mx-auto flex items-center justify-between">
                <div className="flex items-center gap-3 cursor-pointer" onClick={() => setView('landing')}>
                  <div className="bg-green-500 p-1.5 rounded-lg">
                    <TrendingUp className="text-black w-5 h-5" />
                  </div>
                  <h1 className="text-lg font-bold tracking-tight">Stock Intelligence</h1>
                </div>
                <div className="flex gap-4">
                  <button 
                    onClick={() => setView('select')}
                    className="text-sm font-bold text-slate-400 hover:text-white transition-colors"
                  >
                    Switch Ticker
                  </button>
                </div>
              </div>
            </nav>

            <main className="max-w-[1400px] mx-auto px-6 py-8">
              {loading && <ProcessingOverlay ticker={ticker} />}
              
              {error && (
                <div className="mb-6 p-4 bg-red-900/20 border border-red-500/30 rounded-2xl flex items-center gap-3 text-red-400">
                  <AlertTriangle className="w-5 h-5" />
                  <p>{error}</p>
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                
                {/* Chart & Core Metrics */}
                <div className="lg:col-span-8 space-y-6">
                  <div className="glass-card p-8">
                    <div className="flex justify-between items-start mb-8">
                      <div>
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-4xl font-black tracking-tighter">{data?.ticker || ticker}</span>
                          <span className="text-xs font-bold text-slate-500 bg-slate-800 px-2 py-1 rounded-md uppercase">
                            {data?.company_name || "Querying Database..."}
                          </span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-5xl font-bold tracking-tight">
                            ${data?.current_price?.toLocaleString() || "---"}
                          </span>
                          <span className={`flex items-center gap-1 font-bold text-lg ${ (data?.day_change_pct || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {(data?.day_change_pct || 0) >= 0 ? <TrendingUp size={20}/> : <TrendingDown size={20}/>}
                            {data?.day_change_pct?.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="h-[400px] w-full mt-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={history}>
                          <defs>
                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                              <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1e293b" />
                          <XAxis dataKey="date" hide />
                          <YAxis domain={['auto', 'auto']} hide />
                          <Tooltip 
                            contentStyle={{ backgroundColor: '#0f172a', borderRadius: '12px', border: '1px solid #334155', boxShadow: '0 20px 25px -5px rgb(0 0 0 / 0.5)' }}
                            itemStyle={{ color: '#22c55e', fontWeight: 'bold' }}
                          />
                          <Area type="monotone" dataKey="price" stroke="#22c55e" strokeWidth={3} fillOpacity={1} fill="url(#colorPrice)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <MetricBox label="Market Cap" value={data?.key_metrics?.market_cap || "---"} icon={<Activity size={16}/>} />
                    <MetricBox label="P/E Ratio" value={data?.key_metrics?.pe_ratio?.toString() || "---"} icon={<BarChart3 size={16}/>} />
                    <MetricBox label="Beta (Risk)" value={data?.key_metrics?.beta?.toString() || "---"} icon={<ShieldCheck size={16}/>} />
                    <MetricBox label="Volatility" value={`${data?.volatility?.toFixed(2)}%` || "---"} icon={<Activity size={16}/>} />
                  </div>

                  <div className="glass-card p-8 border-l-4 border-l-green-500">
                    <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                      <CheckCircle2 className="text-green-500" />
                      Strategic Verdict
                    </h3>
                    <p className="text-slate-300 text-lg leading-relaxed mb-8">
                      {data?.verdict || "System is aggregating agent reports..."}
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {data?.reasoning.map((r, i) => (
                        <div key={i} className="flex gap-4 p-4 rounded-xl bg-slate-800/30 border border-slate-700/50 text-sm text-slate-400 leading-relaxed">
                          <div className="mt-1 w-2 h-2 rounded-full bg-green-500 shrink-0 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                          {r}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Sidebar: Verdict & Intelligence */}
                <div className="lg:col-span-4 space-y-6">
                  
                  <div className="glass-card p-8 bg-gradient-to-br from-green-600 to-green-900 border-none shadow-[0_0_40px_rgba(34,197,94,0.15)]">
                    <div className="space-y-8">
                      <div>
                        <label className="text-green-200 text-xs font-black uppercase tracking-[0.2em]">Analyst Rating</label>
                        <div className="text-5xl font-black mt-2 tracking-tight text-white drop-shadow-lg">
                          {data?.recommendation || "---"}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-6">
                        <div>
                          <label className="text-green-200 text-xs font-black uppercase tracking-[0.2em]">Target Price</label>
                          <div className="text-3xl font-bold mt-1 text-white">
                            ${data?.target_price || "---"}
                          </div>
                        </div>
                        <div>
                          <label className="text-green-200 text-xs font-black uppercase tracking-[0.2em]">Confidence</label>
                          <div className="text-3xl font-bold mt-1 text-white">
                            {data?.confidence_score ? `${(data.confidence_score * 100).toFixed(0)}%` : "---"}
                          </div>
                        </div>
                      </div>

                      <div className="pt-6 border-t border-white/10 space-y-3">
                        <div className="flex justify-between items-center text-sm font-bold">
                          <span className="text-green-100">Risk Profile</span>
                          <span className="bg-white/20 px-3 py-1 rounded-full uppercase tracking-widest text-[10px]">
                            {data?.risk_level || "---"}
                          </span>
                        </div>
                        <div className="flex justify-between items-center text-sm font-bold">
                          <span className="text-green-100">Time Horizon</span>
                          <span className="text-white">{data?.time_horizon || "---"}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="glass-card flex flex-col h-[600px]">
                    <div className="p-6 border-b border-slate-800 flex items-center justify-between">
                      <h3 className="font-bold flex items-center gap-2">
                        <Newspaper size={18} className="text-green-500" />
                        Intelligence Feed
                      </h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                      {data?.news_summary.map((news, i) => (
                        <div key={i} className="group cursor-pointer">
                          <div className="flex justify-between items-center mb-2">
                            <span className={`text-[10px] font-black px-2 py-0.5 rounded uppercase ${
                              news.sentiment.toLowerCase().includes('bullish') ? 'bg-green-500/10 text-green-500' : 
                              news.sentiment.toLowerCase().includes('bearish') ? 'bg-red-500/10 text-red-500' : 'bg-slate-500/10 text-slate-500'
                            }`}>
                              {news.sentiment}
                            </span>
                            <span className="text-[10px] text-slate-500 flex items-center gap-1 font-bold">
                              <Clock size={10} /> {news.date}
                            </span>
                          </div>
                          <h4 className="text-sm font-bold text-slate-100 group-hover:text-green-400 transition-colors leading-snug mb-2">
                            {news.title}
                          </h4>
                          <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">{news.summary}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              </div>
            </main>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: React.ReactNode, title: string, desc: string }) {
  return (
    <div className="glass-card p-6 bg-slate-900/40">
      <div className="mb-4">{icon}</div>
      <h3 className="font-bold text-lg mb-1">{title}</h3>
      <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
    </div>
  );
}

function MetricBox({ label, value, icon }: { label: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="glass-card p-6 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-slate-500">
        {icon}
        <span className="text-[10px] font-black uppercase tracking-[0.2em]">{label}</span>
      </div>
      <div className="text-xl font-bold text-slate-100 tracking-tight">{value}</div>
    </div>
  );
}

function ProcessingOverlay({ ticker }: { ticker: string }) {
  return (
    <motion.div 
      initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-md flex flex-col items-center justify-center p-6 text-center"
    >
      <div className="relative mb-8">
        <Loader2 className="w-20 h-20 text-green-500 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center font-black text-xs">
          AI
        </div>
      </div>
      <h2 className="text-3xl font-black tracking-tighter mb-2 italic">DEPLOYING AGENT SWARM FOR {ticker}</h2>
      <div className="max-w-md space-y-4">
        <div className="text-xs text-green-500/70 font-mono tracking-widest uppercase">
          Executing Data Research... OK
        </div>
        <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
          <motion.div 
            initial={{ width: "0%" }} animate={{ width: "100%" }}
            transition={{ duration: 15, ease: "linear" }}
            className="h-full bg-green-500"
          />
        </div>
        <p className="text-slate-400 text-sm">
          Please wait as our agents fetch NASDAQ fundamentals, evaluate real-time sentiment, and compute technical volatility models.
        </p>
      </div>
    </motion.div>
  );
}
