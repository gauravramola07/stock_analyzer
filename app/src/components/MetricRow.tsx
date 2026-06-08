import { useAnimatedNumber } from '../hooks/useAnimatedNumber';

interface MetricRowProps {
  label: string;
  value: string | number | null | undefined;
  color?: string;
  prefix?: string;
  suffix?: string;
  decimals?: number;
}

export default function MetricRow({ label, value, color, prefix = '', suffix = '', decimals = 2 }: MetricRowProps) {
  const isNumeric = value !== null && value !== undefined && value !== '—' && !Number.isNaN(Number(value));
  const animatedValue = useAnimatedNumber(isNumeric ? Number(value) : null, 600, decimals);

  const displayValue = isNumeric ? `${prefix}${animatedValue}${suffix}` : (value || '—');

  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span
        className="metric-value"
        style={color ? { color } : undefined}
      >
        {displayValue}
      </span>
    </div>
  );
}
