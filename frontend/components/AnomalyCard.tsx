"use client";

import { useState } from "react";
import { metricLabel, typeMeta } from "@/lib/format";
import type { Anomaly } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

export function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  const [open, setOpen] = useState(false);
  const meta = typeMeta(anomaly.anomaly_type);

  return (
    <article className="card">
      <button
        className="card__head"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="card__icon" aria-hidden>
          {meta.icon}
        </span>
        <span className="card__title">
          <span className="card__type">{meta.label}</span>
          <span className="card__meta">
            {anomaly.tenant_id} · {anomaly.metric_date}
          </span>
        </span>
        <span className="card__score">
          <span className="card__scoreval">{anomaly.anomaly_score.toFixed(3)}</span>
          <span className="card__scorelabel">score</span>
        </span>
        <StatusBadge status={anomaly.status} />
        <span className={`chevron ${open ? "chevron--open" : ""}`} aria-hidden>
          ▾
        </span>
      </button>

      <div className="chips">
        {anomaly.top_contributors.map(([m, z]) => (
          <span className={`chip ${z < 0 ? "chip--down" : "chip--up"}`} key={m}>
            {metricLabel(m)} {z > 0 ? "+" : ""}
            {z.toFixed(1)}σ
          </span>
        ))}
        <span className="chip chip--muted">confidence {anomaly.type_confidence.toFixed(2)}</span>
      </div>

      {open && (
        <div className="card__body">
          <p className="explanation">{anomaly.explanation}</p>
          <div className="grounding">
            <div className="faith">
              <div className="faith__bar">
                <div
                  className="faith__fill"
                  style={{ width: `${Math.round(anomaly.faithfulness * 100)}%` }}
                />
              </div>
              <span className="faith__label">
                faithfulness {anomaly.faithfulness.toFixed(2)}
              </span>
            </div>
            <div className="sources">
              sources: {anomaly.sources.map((s) => (
                <code key={s}>{s}</code>
              ))}
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
