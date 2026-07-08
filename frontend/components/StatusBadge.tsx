import { STATUS_META } from "@/lib/format";
import type { AlertStatus } from "@/lib/types";

export function StatusBadge({ status, sm }: { status: AlertStatus; sm?: boolean }) {
  const meta = STATUS_META[status] ?? { label: status, tone: "warn" };
  return (
    <span className={`badge badge--${meta.tone}${sm ? " badge--sm" : ""}`} role="status">
      {meta.label}
    </span>
  );
}
