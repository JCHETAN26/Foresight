import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AnomalyCard } from "@/components/AnomalyCard";
import { StatTiles } from "@/components/StatTiles";
import type { Anomaly } from "@/lib/types";

const anomaly: Anomaly = {
  tenant_id: "acct_016",
  metric_date: "2026-06-14",
  anomaly_type: "payment_failure",
  anomaly_score: 0.982,
  type_confidence: 0.71,
  top_contributors: [
    ["refund_rate", 9.8],
    ["mrr", -3.2],
  ],
  metrics: { mrr: 41200, refund_rate: 0.16 },
  explanation: "Refund rate spiked while MRR dipped, consistent with card declines.",
  faithfulness: 1.0,
  sources: ["runbook_payment_failure"],
  status: "ready",
};

describe("AnomalyCard", () => {
  it("shows type, drivers, and status; hides explanation until expanded", () => {
    render(<AnomalyCard anomaly={anomaly} />);
    expect(screen.getByText("Payment failure")).toBeInTheDocument();
    expect(screen.getByText(/refund rate/i)).toBeInTheDocument();
    expect(screen.getByText("Alert ready")).toBeInTheDocument();
    expect(screen.queryByText(/card declines/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText(/card declines/i)).toBeInTheDocument();
    expect(screen.getByText(/faithfulness 1.00/)).toBeInTheDocument();
  });
});

describe("StatTiles", () => {
  it("counts ready vs held and averages faithfulness", () => {
    const held: Anomaly = { ...anomaly, status: "held_for_review", faithfulness: 0.8 };
    render(<StatTiles anomalies={[anomaly, held]} />);
    expect(screen.getByText("Anomalies detected").previousSibling).toHaveTextContent("2");
    expect(screen.getByText("Avg faithfulness").previousSibling).toHaveTextContent("0.90");
  });
});
