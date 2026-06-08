interface DataCellProps {
  label: string;
  value: string | number | null | undefined;
}

export default function DataCell({ label, value }: DataCellProps) {
  return (
    <div className="data-cell">
      <div className="data-cell-label">{label}</div>
      <div className="data-cell-value">{value || '—'}</div>
    </div>
  );
}
