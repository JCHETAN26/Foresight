import type { AlertStatus } from "./types";

export const TYPE_META: Record<string, { label: string; icon: string }> = {
  payment_failure: { label: "Payment failure", icon: "💳" },
  churn_spike: { label: "Churn spike", icon: "📉" },
  seasonal_dip: { label: "Seasonal dip", icon: "🗓️" },
  acquisition_drop: { label: "Acquisition drop", icon: "🧲" },
  pricing_effect: { label: "Pricing effect", icon: "🏷️" },
  infrastructure_issue: { label: "Infrastructure issue", icon: "🚨" },
};

export const STATUS_META: Record<AlertStatus, { label: string; tone: string }> = {
  ready: { label: "Alert ready", tone: "ok" },
  sent: { label: "Sent to Slack", tone: "ok" },
  held_for_review: { label: "Held — review", tone: "warn" },
  held_low_faithfulness: { label: "Held — low faithfulness", tone: "danger" },
};

export function typeMeta(type: string) {
  return TYPE_META[type] ?? { label: type.replace(/_/g, " "), icon: "⚠️" };
}

export function metricLabel(metric: string): string {
  return metric.replace(/_/g, " ");
}

/** Severity colour from the anomaly score (0..1). */
export function severityColor(score: number): string {
  if (score >= 0.97) return "var(--sev-high)";
  if (score >= 0.9) return "var(--sev-mid)";
  return "var(--sev-low)";
}

export type MetricKind = "currency" | "percent" | "count";

export function metricKind(metric: string): MetricKind {
  if (metric === "mrr") return "currency";
  if (metric === "conversion_rate" || metric === "refund_rate") return "percent";
  return "count";
}

/** Compact, human formatting per metric type. */
export function formatMetric(metric: string, value: number): string {
  switch (metricKind(metric)) {
    case "currency":
      return value >= 1000 ? `$${(value / 1000).toFixed(1)}k` : `$${value.toFixed(0)}`;
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    default:
      return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value.toFixed(0);
  }
}

export function faithColor(f: number): string {
  if (f >= 0.9) return "var(--ok)";
  if (f >= 0.75) return "var(--warn)";
  return "var(--danger)";
}
