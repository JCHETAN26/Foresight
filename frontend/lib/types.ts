export type AlertStatus =
  | "ready"
  | "held_for_review"
  | "held_low_faithfulness"
  | "sent";

export interface Anomaly {
  tenant_id: string;
  metric_date: string;
  anomaly_type: string;
  anomaly_score: number;
  type_confidence: number;
  top_contributors: [string, number][];
  metrics: Record<string, number>;
  explanation: string;
  faithfulness: number;
  sources: string[];
  status: AlertStatus;
}

export interface DemoBundle {
  generated_with: string;
  anomalies: Anomaly[];
}
