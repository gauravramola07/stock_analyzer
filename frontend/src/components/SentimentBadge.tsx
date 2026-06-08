type Sentiment = 'Bullish' | 'Bearish' | 'Neutral';

interface SentimentBadgeProps {
  sentiment: Sentiment | string;
}

export default function SentimentBadge({ sentiment }: SentimentBadgeProps) {
  const s = (sentiment || 'Neutral') as Sentiment;
  const cfg: Record<Sentiment, string> = {
    Bullish: 'sentiment-bullish',
    Bearish: 'sentiment-bearish',
    Neutral: 'sentiment-neutral',
  };

  return (
    <span className={`sentiment-badge ${cfg[s] || cfg.Neutral}`}>
      {s.toUpperCase()}
    </span>
  );
}
