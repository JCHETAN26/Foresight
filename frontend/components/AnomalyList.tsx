"use client";

import { severityColor, typeMeta } from "@/lib/format";
import type { Anomaly } from "@/lib/types";

export const keyOf = (a: Anomaly) => `${a.tenant_id}-${a.metric_date}-${a.anomaly_type}`;

export function AnomalyList({
  anomalies,
  selectedKey,
  onSelect,
}: {
  anomalies: Anomaly[];
  selectedKey: string;
  onSelect: (a: Anomaly) => void;
}) {
  return (
    <div className="panel">
      <div className="panel__head">
        <h2>Detected anomalies</h2>
        <span className="panel__count">{anomalies.length} events</span>
      </div>
      <div className="alist">
        {anomalies.map((a) => {
          const meta = typeMeta(a.anomaly_type);
          const active = keyOf(a) === selectedKey;
          return (
            <button
              key={keyOf(a)}
              className={`arow${active ? " arow--active" : ""}`}
              onClick={() => onSelect(a)}
              aria-pressed={active}
            >
              <span className="arow__ico" aria-hidden>
                {meta.icon}
              </span>
              <span className="arow__main">
                <span className="arow__type">{meta.label}</span>
                <span className="arow__meta">
                  {a.tenant_id} · {a.metric_date}
                </span>
              </span>
              <span className="arow__right">
                <span className="sevbar" title={`score ${a.anomaly_score.toFixed(3)}`}>
                  <span
                    className="sevbar__fill"
                    style={{
                      width: `${Math.round(a.anomaly_score * 100)}%`,
                      background: severityColor(a.anomaly_score),
                    }}
                  />
                </span>
                <span className="sevscore">{a.anomaly_score.toFixed(2)}</span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
