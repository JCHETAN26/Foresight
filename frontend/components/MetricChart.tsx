"use client";

import { metricKind } from "@/lib/format";

interface Point {
  date: string;
  value: number;
}

/** Dependency-free SVG line chart with the anomaly day marked. */
export function MetricChart({
  metric,
  points,
  anomalyDate,
}: {
  metric: string;
  points: Point[];
  anomalyDate: string;
}) {
  const W = 720;
  const H = 210;
  const padL = 8;
  const padR = 8;
  const padT = 14;
  const padB = 10;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  if (points.length < 2) {
    return <div className="empty" style={{ minHeight: 120 }}>Not enough history to chart.</div>;
  }

  const values = points.map((p) => p.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const pad = (max - min) * 0.12;
  min -= pad;
  max += pad;

  const x = (i: number) => padL + (i / (points.length - 1)) * innerW;
  const y = (v: number) => padT + innerH * (1 - (v - min) / (max - min));

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`)
    .join(" ");
  const areaPath =
    `M${x(0).toFixed(1)},${y(points[0].value).toFixed(1)} ` +
    points.map((p, i) => `L${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ") +
    ` L${x(points.length - 1).toFixed(1)},${(padT + innerH).toFixed(1)}` +
    ` L${x(0).toFixed(1)},${(padT + innerH).toFixed(1)} Z`;

  const anomalyIdx = points.findIndex((p) => p.date === anomalyDate);
  const kind = metricKind(metric);
  const fmtAxis = (v: number) =>
    kind === "percent"
      ? `${(v * 100).toFixed(0)}%`
      : kind === "currency"
        ? `$${Math.round(v / 1000)}k`
        : Math.round(v).toString();

  const gid = `grad-${metric}`;
  const short = (d: string) => d.slice(5); // MM-DD

  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${metric} over time`}>
        <defs>
          <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* horizontal gridlines + y labels */}
        {[0, 0.5, 1].map((t) => {
          const gy = padT + innerH * t;
          const val = max - (max - min) * t;
          return (
            <g key={t}>
              <line
                x1={padL}
                x2={W - padR}
                y1={gy}
                y2={gy}
                stroke="var(--border)"
                strokeWidth="1"
              />
              <text x={padL + 2} y={gy - 3} fontSize="10" fill="var(--faint)">
                {fmtAxis(val)}
              </text>
            </g>
          );
        })}

        <path d={areaPath} fill={`url(#${gid})`} />
        <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" />

        {anomalyIdx >= 0 && (
          <g>
            <line
              x1={x(anomalyIdx)}
              x2={x(anomalyIdx)}
              y1={padT}
              y2={padT + innerH}
              stroke="var(--danger)"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
            <circle cx={x(anomalyIdx)} cy={y(points[anomalyIdx].value)} r="6" fill="var(--surface)" stroke="var(--danger)" strokeWidth="2.5" />
            <circle cx={x(anomalyIdx)} cy={y(points[anomalyIdx].value)} r="2.5" fill="var(--danger)" />
          </g>
        )}
      </svg>
      <div className="chart-x">
        <span>{short(points[0].date)}</span>
        {anomalyIdx > 1 && anomalyIdx < points.length - 2 && (
          <span style={{ color: "var(--danger)", fontWeight: 600 }}>{short(anomalyDate)}</span>
        )}
        <span>{short(points[points.length - 1].date)}</span>
      </div>
    </div>
  );
}
