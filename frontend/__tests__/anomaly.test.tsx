import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AnomalyDetail } from "@/components/AnomalyDetail";
import { AnomalyList } from "@/components/AnomalyList";
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
  metrics: { mrr: 41200, refund_rate: 0.16, conversion_rate: 0.29, checkout_volume: 880 },
  explanation: "Refund rate spiked while MRR dipped, consistent with card declines.",
  faithfulness: 1.0,
  sources: ["runbook_payment_failure"],
  status: "ready",
};

describe("AnomalyList", () => {
  it("renders a row per anomaly and reports selection", () => {
    const onSelect = vi.fn();
    render(
      <AnomalyList anomalies={[anomaly]} selectedKey="" onSelect={onSelect} />,
    );
    expect(screen.getByText("Payment failure")).toBeInTheDocument();
    expect(screen.getByText(/acct_016/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledWith(anomaly);
  });
});

describe("AnomalyDetail", () => {
  it("shows the explanation, drivers, faithfulness and status", () => {
    render(<AnomalyDetail anomaly={anomaly} kpis={null} loading={false} />);
    expect(screen.getByText("Payment failure")).toBeInTheDocument();
    expect(screen.getByText("Alert ready")).toBeInTheDocument();
    expect(screen.getByText(/card declines/i)).toBeInTheDocument();
    expect(screen.getByText("1.00")).toBeInTheDocument(); // faithfulness value
    expect(screen.getByText("runbook_payment_failure")).toBeInTheDocument();
    // driver metric contribution surfaced as a sigma badge
    expect(screen.getByText("+9.8σ")).toBeInTheDocument();
  });
});

describe("StatTiles", () => {
  it("counts ready vs held and averages faithfulness", () => {
    const held: Anomaly = { ...anomaly, status: "held_for_review", faithfulness: 0.8 };
    render(<StatTiles anomalies={[anomaly, held]} />);
    expect(screen.getByText("Anomalies detected").closest(".tile")).toHaveTextContent("2");
    expect(screen.getByText("Held for review").closest(".tile")).toHaveTextContent("1");
    expect(screen.getByText("Avg faithfulness").closest(".tile")).toHaveTextContent("0.90");
  });
});
