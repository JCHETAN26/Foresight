import type { Anomaly } from "@/lib/types";

export function StatTiles({ anomalies }: { anomalies: Anomaly[] }) {
  const ready = anomalies.filter((a) => a.status === "ready" || a.status === "sent").length;
  const held = anomalies.length - ready;
  const avgFaith =
    anomalies.reduce((s, a) => s + a.faithfulness, 0) / (anomalies.length || 1);

  const tiles = [
    { label: "Anomalies detected", value: anomalies.length },
    { label: "Alerts ready", value: ready },
    { label: "Held for review", value: held },
    { label: "Avg faithfulness", value: avgFaith.toFixed(2) },
  ];

  return (
    <div className="tiles">
      {tiles.map((t) => (
        <div className="tile" key={t.label}>
          <div className="tile__value">{t.value}</div>
          <div className="tile__label">{t.label}</div>
        </div>
      ))}
    </div>
  );
}
