import { AnomalyCard } from "@/components/AnomalyCard";
import { StatTiles } from "@/components/StatTiles";
import type { DemoBundle } from "@/lib/types";
import bundle from "@/public/demo-data.json";

const data = bundle as unknown as DemoBundle;

export default function Home() {
  const anomalies = [...data.anomalies].sort((a, b) => b.anomaly_score - a.anomaly_score);

  return (
    <main className="page">
      <header className="masthead">
        <div className="brand">
          <span className="brand__mark">◆</span> Foresight
        </div>
        <h1>Revenue intelligence, explained.</h1>
        <p className="lede">
          Anomalies detected across tenant KPIs, classified by type, and explained
          in plain English by a grounded LangGraph agent — every claim traced to the
          metrics and retrieved context.
        </p>
      </header>

      <StatTiles anomalies={data.anomalies} />

      <section className="timeline">
        <div className="timeline__head">
          <h2>Anomaly timeline</h2>
          <span className="timeline__note">
            explanations generated with {data.generated_with}
          </span>
        </div>
        {anomalies.map((a) => (
          <AnomalyCard key={`${a.tenant_id}-${a.metric_date}-${a.anomaly_type}`} anomaly={a} />
        ))}
      </section>

      <footer className="footer">
        Detection: LSTM-AE + IsolationForest ensemble · Classification: TF-IDF /
        LoRA-T5 · Explanation: freshness-aware RAG + Claude with a faithfulness gate.
      </footer>
    </main>
  );
}
