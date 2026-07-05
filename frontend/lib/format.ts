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
  held_for_review: { label: "Held — human review", tone: "warn" },
  held_low_faithfulness: { label: "Held — low faithfulness", tone: "danger" },
};

export function typeMeta(type: string) {
  return TYPE_META[type] ?? { label: type, icon: "⚠️" };
}

export function metricLabel(metric: string): string {
  return metric.replace(/_/g, " ");
}
