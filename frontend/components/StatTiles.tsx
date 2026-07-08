import type { Anomaly } from "@/lib/types";

export function StatTiles({ anomalies }: { anomalies: Anomaly[] }) {
  const ready = anomalies.filter((a) => a.status === "ready" || a.status === "sent").length;
  const held = anomalies.length - ready;
  const avgFaith =
    anomalies.reduce((s, a) => s + a.faithfulness, 0) / (anomalies.length || 1);

  const tiles = [
    { label: "Anomalies detected", value: anomalies.length, sub: "last 120 days", dot: "var(--accent)" },
    { label: "Alerts ready", value: ready, sub: "grounded & sendable", dot: "var(--ok)" },
    { label: "Held for review", value: held, sub: "low type-confidence", dot: "var(--warn)" },
    { label: "Avg faithfulness", value: avgFaith.toFixed(2), sub: "claims traced to data", dot: "var(--accent-2)" },
  ];

  return (
    <div className="tiles">
      {tiles.map((t) => (
        <div className="tile" key={t.label}>
          <div className="tile__label">
            <span className="tile__dot" style={{ background: t.dot }} />
            {t.label}
          </div>
          <div className="tile__value">{t.value}</div>
          <div className="tile__sub">{t.sub}</div>
        </div>
      ))}
    </div>
  );
}
