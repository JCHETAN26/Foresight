"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Anomaly, KpiPoint } from "@/lib/types";
import { AnomalyDetail } from "./AnomalyDetail";
import { AnomalyList, keyOf } from "./AnomalyList";
import { Sidebar } from "./Sidebar";
import { StatTiles } from "./StatTiles";

/**
 * Renders the precomputed bundle immediately (SSR / static export), then, if
 * NEXT_PUBLIC_API_URL is configured, replaces it with live data from the API and
 * pulls the KPI trend for whichever anomaly is selected.
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
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [kpiCache, setKpiCache] = useState<Record<string, KpiPoint[]>>({});
  const [kpiLoading, setKpiLoading] = useState(false);
  const touched = useRef(false);

  const sorted = useMemo(
    () => [...anomalies].sort((a, b) => b.anomaly_score - a.anomaly_score),
    [anomalies],
  );

  // Load live anomalies.
  useEffect(() => {
    if (!apiUrl) return;
    fetch(`${apiUrl}/anomalies`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: Anomaly[]) => {
        setAnomalies(data);
        setLive(true);
        // Select the highest-severity anomaly unless the user already picked one.
        if (!touched.current && data.length) {
          const top = [...data].sort((a, b) => b.anomaly_score - a.anomaly_score)[0];
          setSelectedKey(keyOf(top));
        }
      })
      .catch(() => {
        /* keep the precomputed bundle */
      });
  }, [apiUrl]);

  // Default selection = highest-severity anomaly.
  useEffect(() => {
    if (!selectedKey && sorted.length) setSelectedKey(keyOf(sorted[0]));
  }, [sorted, selectedKey]);

  const selected = sorted.find((a) => keyOf(a) === selectedKey) ?? sorted[0];
  const tenantCount = useMemo(
    () => new Set(anomalies.map((a) => a.tenant_id)).size,
    [anomalies],
  );

  // Load KPI trend for the selected tenant (cached per tenant).
  useEffect(() => {
    if (!apiUrl || !selected) return;
    const tenant = selected.tenant_id;
    if (kpiCache[tenant]) return;
    setKpiLoading(true);
    fetch(`${apiUrl}/kpis/${tenant}?days=120`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((pts: KpiPoint[]) => setKpiCache((c) => ({ ...c, [tenant]: pts })))
      .catch(() => setKpiCache((c) => ({ ...c, [tenant]: [] })))
      .finally(() => setKpiLoading(false));
  }, [apiUrl, selected, kpiCache]);

  const kpis = selected ? (kpiCache[selected.tenant_id] ?? null) : null;

  return (
    <div className="app">
      <Sidebar live={live} tenantCount={tenantCount} />
      <main className="main">
        <div className="topbar">
          <div>
            <h1>Revenue anomalies</h1>
            <p>
              Detected across tenant KPIs, classified by type, and explained in
              plain English by a grounded agent — every claim traced to the metrics
              and retrieved context.
            </p>
          </div>
          <div className="topbar__right">
            <span className="livepill">
              <span className={`livedot ${live ? "" : "livedot--off"}`} />
              {live ? "Live" : `by ${generatedWith}`}
            </span>
          </div>
        </div>

        <StatTiles anomalies={anomalies} />

        <div className="split">
          <AnomalyList
            anomalies={sorted}
            selectedKey={selectedKey || (selected ? keyOf(selected) : "")}
            onSelect={(a) => {
              touched.current = true;
              setSelectedKey(keyOf(a));
            }}
          />
          {selected ? (
            <AnomalyDetail anomaly={selected} kpis={kpis} loading={kpiLoading && !kpis} />
          ) : (
            <div className="panel empty">No anomalies to show.</div>
          )}
        </div>
      </main>
    </div>
  );
}
