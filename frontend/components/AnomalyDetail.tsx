"use client";

import { faithColor, formatMetric, metricLabel, typeMeta } from "@/lib/format";
import type { Anomaly, KpiPoint } from "@/lib/types";
import { MetricChart } from "./MetricChart";
import { StatusBadge } from "./StatusBadge";

const METRIC_ORDER = ["mrr", "conversion_rate", "refund_rate", "checkout_volume"];

export function AnomalyDetail({
  anomaly,
  kpis,
  loading,
}: {
  anomaly: Anomaly;
  kpis: KpiPoint[] | null;
  loading: boolean;
}) {
  const meta = typeMeta(anomaly.anomaly_type);
  const driver = anomaly.top_contributors[0]?.[0] ?? "mrr";
  const zByMetric = Object.fromEntries(anomaly.top_contributors);

  const chartPoints =
    kpis?.map((p) => ({
      date: p.metric_date,
      value: (p[driver as keyof KpiPoint] as number) ?? 0,
    })) ?? [];

  return (
    <div className="panel detail">
      <div className="detail__head">
        <span className="detail__ico" aria-hidden>
          {meta.icon}
        </span>
        <div className="detail__titles">
          <h2 className="detail__type">{meta.label}</h2>
          <div className="detail__sub">
            {anomaly.tenant_id} · {anomaly.metric_date} · score{" "}
            {anomaly.anomaly_score.toFixed(3)} · type confidence{" "}
            {anomaly.type_confidence.toFixed(2)}
          </div>
        </div>
        <StatusBadge status={anomaly.status} />
      </div>

      <div className="detail__body">
        <section>
          <p className="detail__sectlabel">KPIs on {anomaly.metric_date}</p>
          <div className="metrics-row">
            {METRIC_ORDER.map((m) => {
              const z = zByMetric[m];
              return (
                <div key={m} className={`mcard${m === driver ? " mcard--driver" : ""}`}>
                  <div className="mcard__k">{metricLabel(m)}</div>
                  <div className="mcard__v">
                    {formatMetric(m, anomaly.metrics[m] ?? 0)}
                  </div>
                  <div
                    className={`mcard__z ${z == null ? "z-flat" : z < 0 ? "z-down" : "z-up"}`}
                  >
                    {z == null ? "in range" : `${z > 0 ? "+" : ""}${z.toFixed(1)}σ`}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section>
          <p className="detail__sectlabel">
            {metricLabel(driver)} — the primary driver
          </p>
          <div className="chart-wrap">
            <div className="chart-head">
              <span className="chart-title">{metricLabel(driver)}</span>
              <span className="chart-legend">
                <span className="legend-dot" /> anomaly day
              </span>
            </div>
            {loading ? (
              <div className="empty" style={{ minHeight: 120 }}>Loading trend…</div>
            ) : (
              <MetricChart
                metric={driver}
                points={chartPoints}
                anomalyDate={anomaly.metric_date}
              />
            )}
          </div>
        </section>

        <section>
          <p className="detail__sectlabel">AI explanation</p>
          <div className="explain">
            <div className="explain__ai">
              <span className="explain__badge">Claude</span>
              grounded via freshness-aware RAG + faithfulness gate
            </div>
            <p>{anomaly.explanation}</p>
            <div className="grounding">
              <span className="faith">
                <span className="faith__bar">
                  <span
                    className="faith__fill"
                    style={{
                      width: `${Math.round(anomaly.faithfulness * 100)}%`,
                      background: faithColor(anomaly.faithfulness),
                    }}
                  />
                </span>
                faithfulness{" "}
                <span className="faith__val">{anomaly.faithfulness.toFixed(2)}</span>
              </span>
              {anomaly.sources.length > 0 && (
                <span className="sources">
                  sources
                  {anomaly.sources.map((s) => (
                    <code key={s}>{s}</code>
                  ))}
                </span>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
