"use client";

import { useEffect, useState } from "react";
import type { Anomaly } from "@/lib/types";
import { AnomalyCard } from "./AnomalyCard";
import { StatTiles } from "./StatTiles";

/**
 * Renders the precomputed bundle immediately (SSR / static export), then, if
 * NEXT_PUBLIC_API_URL is configured, replaces it with live data from the M4 API.
 */
export function Dashboard({
  initial,
  apiUrl,
  generatedWith,
}: {
  initial: Anomaly[];
  apiUrl?: string;
  generatedWith: string;
}) {
  const [anomalies, setAnomalies] = useState(initial);
  const [live, setLive] = useState(false);

  useEffect(() => {
    if (!apiUrl) return;
    fetch(`${apiUrl}/anomalies`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: Anomaly[]) => {
        setAnomalies(data);
        setLive(true);
      })
      .catch(() => {
        /* keep the precomputed bundle */
      });
  }, [apiUrl]);

  const sorted = [...anomalies].sort((a, b) => b.anomaly_score - a.anomaly_score);

  return (
    <>
      <StatTiles anomalies={anomalies} />
      <section className="timeline">
        <div className="timeline__head">
          <h2>Anomaly timeline</h2>
          <span className="timeline__note">
            {live ? "live from the API" : `explanations by ${generatedWith}`}
          </span>
        </div>
        {sorted.map((a) => (
          <AnomalyCard key={`${a.tenant_id}-${a.metric_date}-${a.anomaly_type}`} anomaly={a} />
        ))}
      </section>
    </>
  );
}
