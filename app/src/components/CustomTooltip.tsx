interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}

export default function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: 'color-mix(in srgb, var(--base) 97%, transparent)',
        border: '1px solid var(--border-accent)',
        borderRadius: 10,
        padding: '10px 16px',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: '0 0 30px var(--accent-glow)',
      }}
    >
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          letterSpacing: '0.15em',
          color: 'var(--text-muted)',
          marginBottom: 5,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 20,
          fontWeight: 700,
          color: 'var(--accent)',
        }}
      >
        ${Number(payload[0].value).toFixed(2)}
      </div>
    </div>
  );
}
