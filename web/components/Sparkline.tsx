"use client";

export function Sparkline({ values, color }: { values: number[]; color: string }) {
  if (!values.length) return <div className="h-8" />;
  const w = 120;
  const h = 32;
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
      <polyline fill="none" stroke={color} strokeWidth="1.5" points={pts.join(" ")} />
      <circle cx={last[0]} cy={last[1]} r="2" fill={color} />
    </svg>
  );
}
