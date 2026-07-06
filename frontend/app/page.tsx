import { Dashboard } from "@/components/Dashboard";
import type { DemoBundle } from "@/lib/types";
import bundle from "@/public/demo-data.json";

const data = bundle as unknown as DemoBundle;

export default function Home() {
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

      <Dashboard
        initial={data.anomalies}
        apiUrl={process.env.NEXT_PUBLIC_API_URL}
        generatedWith={data.generated_with}
      />

      <footer className="footer">
        Detection: LSTM-AE + IsolationForest ensemble · Classification: TF-IDF /
        LoRA-T5 · Explanation: freshness-aware RAG + Claude with a faithfulness gate.
      </footer>
    </main>
  );
}
