interface EmptyStateProps {
  title: string;
  icon: 'search' | 'news' | 'data';
}

const ICONS = {
  search: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: 64, height: 64, marginBottom: 16 }}>
      <circle cx="55" cy="55" r="35" stroke="var(--text-muted)" strokeWidth="2" strokeDasharray="4 4" opacity="0.5" />
      <path d="M80 80L105 105" stroke="var(--text-muted)" strokeWidth="3" strokeLinecap="round" opacity="0.5" />
      <circle cx="55" cy="55" r="25" stroke="var(--accent)" strokeWidth="2" opacity="0.3" />
      <text x="55" y="62" textAnchor="middle" fill="var(--text-secondary)" fontFamily="'JetBrains Mono', monospace" fontSize="18">$</text>
    </svg>
  ),
  news: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: 64, height: 64, marginBottom: 16 }}>
      <rect x="25" y="20" width="70" height="80" rx="6" stroke="var(--text-muted)" strokeWidth="2" opacity="0.5" />
      <line x1="40" y1="45" x2="80" y2="45" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
      <line x1="40" y1="55" x2="70" y2="55" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <line x1="40" y1="65" x2="75" y2="65" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" opacity="0.3" />
      <circle cx="85" cy="85" r="15" fill="var(--void)" stroke="var(--accent)" strokeWidth="2" />
      <path d="M80 85L85 90L93 82" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  data: (
    <svg viewBox="0 0 120 120" fill="none" style={{ width: 64, height: 64, marginBottom: 16 }}>
      <rect x="20" y="60" width="16" height="40" rx="3" stroke="var(--text-muted)" strokeWidth="2" opacity="0.4" />
      <rect x="44" y="40" width="16" height="60" rx="3" stroke="var(--text-muted)" strokeWidth="2" opacity="0.4" />
      <rect x="68" y="50" width="16" height="50" rx="3" stroke="var(--accent)" strokeWidth="2" opacity="0.5" />
      <line x1="15" y1="95" x2="105" y2="95" stroke="var(--text-muted)" strokeWidth="2" opacity="0.3" />
    </svg>
  ),
};

export default function EmptyState({ title, icon }: EmptyStateProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 20px' }}>
      {ICONS[icon]}
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: 'var(--text-secondary)', letterSpacing: '0.1em' }}>
        {title}
      </span>
    </div>
  );
}
