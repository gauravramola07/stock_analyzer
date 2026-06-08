import { TrendingUp, TrendingDown } from 'lucide-react';

const TICKER_DATA = [
  { symbol: 'AAPL', price: 189.45, change: 1.24 },
  { symbol: 'NVDA', price: 875.28, change: 3.56 },
  { symbol: 'TSLA', price: 172.45, change: -0.82 },
  { symbol: 'MSFT', price: 420.55, change: 0.95 },
  { symbol: 'AMZN', price: 178.12, change: 1.88 },
  { symbol: 'GOOGL', price: 165.33, change: 0.42 },
  { symbol: 'META', price: 505.75, change: 2.15 },
  { symbol: 'AMD', price: 182.45, change: -1.23 },
  { symbol: 'NFLX', price: 628.90, change: 4.55 },
  { symbol: 'INTC', price: 43.12, change: -0.35 },
  { symbol: 'CRM', price: 285.60, change: 1.12 },
  { symbol: 'ADBE', price: 520.45, change: -2.18 },
  { symbol: 'PYPL', price: 62.35, change: 0.78 },
  { symbol: 'UBER', price: 78.90, change: 1.45 },
  { symbol: 'COIN', price: 198.50, change: 5.22 },
];

export default function TickerStrip() {
  const items = [...TICKER_DATA, ...TICKER_DATA];

  return (
    <div className="ticker-strip">
      <div className="ticker-row">
        {items.map((item, idx) => (
          <div key={`${item.symbol}-${idx}`} className="ticker-item">
            <span className="ticker-symbol">{item.symbol}</span>
            <span>${item.price.toFixed(2)}</span>
            <span
              style={{
                color: item.change >= 0 ? 'var(--gain)' : 'var(--loss)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              {item.change >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {item.change >= 0 ? '+' : ''}
              {item.change.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
