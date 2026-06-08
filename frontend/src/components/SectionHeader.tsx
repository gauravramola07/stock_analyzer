import type { ReactNode } from 'react';

interface SectionHeaderProps {
  icon?: ReactNode;
  label: string;
}

export default function SectionHeader({ icon, label }: SectionHeaderProps) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18 }}>
      {icon && <span style={{ color: 'var(--text-secondary)', display: 'inline-flex' }}>{icon}</span>}
      <span className="section-label">{label}</span>
    </div>
  );
}
