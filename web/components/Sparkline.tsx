"use client";

export function Sparkline({
  values,
  color,
  compact = false,
}: {
  values: number[];
  color: string;
  compact?: boolean;
}) {
  if (!values.length) return <div className={compact ? "h-6" : "h-8"} />;
  const w = compact ? 88 : 140;
  const h = compact ? 24 : 36;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * w;
    const y = h - ((v - min) / span) * (h - 4) - 2;
    return `${x},${y}`;
  });
  const last = pts[pts.length - 1].split(",");
  return (
    <svg width={w} height={h} aria-hidden="true">
      <polyline fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" points={pts.join(" ")} />
      <circle cx={last[0]} cy={last[1]} r="2" fill={color} />
    </svg>
  );
}
