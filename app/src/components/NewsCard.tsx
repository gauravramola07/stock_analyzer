import { ExternalLink } from 'lucide-react';
import SentimentBadge from './SentimentBadge';
import type { NewsArticle } from '../App';

interface NewsCardProps {
  article: NewsArticle;
}

const SENTIMENT_STYLES: Record<string, { bg: string; border: string }> = {
  Bullish: { bg: 'rgba(0, 217, 117, 0.04)', border: 'rgba(0, 217, 117, 0.15)' },
  Bearish: { bg: 'rgba(244, 63, 94, 0.04)', border: 'rgba(244, 63, 94, 0.15)' },
  Neutral: { bg: 'rgba(122, 143, 166, 0.04)', border: 'rgba(122, 143, 166, 0.15)' },
};

export default function NewsCard({ article }: NewsCardProps) {
  const sentiment = (article.sentiment || 'Neutral') as keyof typeof SENTIMENT_STYLES;
  const style = SENTIMENT_STYLES[sentiment] || SENTIMENT_STYLES.Neutral;
  const borderLeftColor = sentiment === 'Bullish' ? 'var(--gain)' : sentiment === 'Bearish' ? 'var(--loss)' : 'var(--text-muted)';

  return (
    <div
      className="news-card"
      style={{
        background: style.bg,
        borderLeft: `3px solid ${borderLeftColor}`,
        border: `1px solid ${style.border}`,
        borderLeftWidth: 3,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 6 }}>
        <div style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.45, flex: 1 }}>
          {article.title || 'Untitled'}
        </div>
        <SentimentBadge sentiment={article.sentiment || 'Neutral'} />
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: 'var(--text-muted)', marginBottom: 8, letterSpacing: '0.1em' }}>
        <span>{article.source || 'Unknown'}</span>
        {article.date && <><span>·</span><span>{article.date}</span></>}
        {article.url && (
          <a href={article.url} target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 3, color: 'var(--info)', textDecoration: 'none' }}>
            <ExternalLink size={9} /> LINK
          </a>
        )}
      </div>

      <p style={{ fontFamily: "'Inter', sans-serif", fontSize: 12, lineHeight: 1.65, color: 'var(--text-secondary)', margin: 0 }}>
        {article.summary || 'No summary available.'}
      </p>
    </div>
  );
}
