interface ReasoningItemProps {
  index: number;
  text: string;
}

export default function ReasoningItem({ index, text }: ReasoningItemProps) {
  return (
    <div className="reasoning-item">
      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: 'var(--accent)', marginRight: 8, letterSpacing: '0.1em' }}>
        {String(index + 1).padStart(2, '0')}
      </span>
      {text}
    </div>
  );
}
