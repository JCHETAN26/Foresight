"""Generate `bronze_stripe_events.csv` — a local stand-in for the Iceberg
bronze table that the Spark streaming job populates in production.

Each row mirrors the ingestion envelope: routing/lineage columns plus the raw
Stripe `data.object` serialized as a JSON string in `payload`. The dbt staging
model parses fields out of `payload` exactly as it will against real bronze.

Run from this directory:  python _generate_bronze_seed.py
Not read by dbt (only *.csv seeds are), kept for reproducibility.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

# Day base epochs (UTC 10:00) — kept in sync with the KPI assertions in tests/.
DAY1 = 1780308000  # 2026-06-01
DAY2 = 1780394400  # 2026-06-02
DAY3 = 1780480800  # 2026-06-03

# (tenant, day_base, offset_s, event_type, object_id, customer, amount_cents,
#  subscription, status)
EVENTS = [
    # ── acct_alpha, Day 1 ────────────────────────────────────────────────
    ("acct_alpha", DAY1, 60, "customer.subscription.created", "sub_a1", "cus_a1", 5000, "sub_a1", "active"),
    ("acct_alpha", DAY1, 120, "customer.subscription.created", "sub_a2", "cus_a2", 10000, "sub_a2", "active"),
    ("acct_alpha", DAY1, 180, "invoice.paid", "in_a1", "cus_a1", 5000, "sub_a1", "paid"),
    ("acct_alpha", DAY1, 240, "invoice.paid", "in_a2", "cus_a2", 10000, "sub_a2", "paid"),
    ("acct_alpha", DAY1, 300, "checkout.session.completed", "cs_a1", "cus_a1", 5000, "", "complete"),
    ("acct_alpha", DAY1, 360, "checkout.session.completed", "cs_a2", "cus_a2", 10000, "", "complete"),
    ("acct_alpha", DAY1, 420, "checkout.session.expired", "cs_a3", "", 5000, "", "expired"),
    # ── acct_alpha, Day 2 ────────────────────────────────────────────────
    ("acct_alpha", DAY2, 60, "customer.subscription.created", "sub_a3", "cus_a3", 5000, "sub_a3", "active"),
    ("acct_alpha", DAY2, 120, "invoice.paid", "in_a3", "cus_a3", 5000, "sub_a3", "paid"),
    ("acct_alpha", DAY2, 180, "invoice.payment_failed", "in_a4", "cus_a2", 10000, "sub_a2", "open"),
    ("acct_alpha", DAY2, 240, "charge.refunded", "ch_a1", "cus_a1", 2000, "", "succeeded"),
    ("acct_alpha", DAY2, 300, "checkout.session.completed", "cs_a4", "cus_a3", 5000, "", "complete"),
    ("acct_alpha", DAY2, 360, "checkout.session.expired", "cs_a5", "", 5000, "", "expired"),
    # ── acct_alpha, Day 3 ────────────────────────────────────────────────
    ("acct_alpha", DAY3, 60, "customer.subscription.deleted", "sub_a1", "cus_a1", 5000, "sub_a1", "canceled"),
    ("acct_alpha", DAY3, 120, "invoice.paid", "in_a5", "cus_a2", 10000, "sub_a2", "paid"),
    ("acct_alpha", DAY3, 180, "invoice.payment_failed", "in_a6", "cus_a3", 5000, "sub_a3", "open"),
    ("acct_alpha", DAY3, 240, "checkout.session.completed", "cs_a6", "cus_a4", 5000, "", "complete"),
    # ── acct_beta ────────────────────────────────────────────────────────
    ("acct_beta", DAY1, 90, "customer.subscription.created", "sub_b1", "cus_b1", 20000, "sub_b1", "active"),
    ("acct_beta", DAY1, 150, "invoice.paid", "in_b1", "cus_b1", 20000, "sub_b1", "paid"),
    ("acct_beta", DAY2, 90, "invoice.paid", "in_b2", "cus_b1", 20000, "sub_b1", "paid"),
]


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for i, (tenant, base, off, etype, obj_id, cust, amount, sub, status) in enumerate(EVENTS, 1):
        created = base + off
        payload = {
            "id": obj_id,
            "customer": cust or None,
            "amount": amount,
            "currency": "usd",
            "subscription": sub or None,
            "status": status,
        }
        rows.append(
            {
                "event_id": f"evt_{i:04d}",
                "source": "stripe",
                "tenant_id": tenant,
                "event_type": etype,
                "livemode": "false",
                "created_epoch": created,
                "api_version": "2024-06-20",
                "payload": json.dumps(payload, separators=(",", ":")),
                "ingested_at": "2026-06-03T12:00:00",
            }
        )
    # Duplicate delivery of one event — silver must dedupe on event_id.
    rows.append(dict(rows[2]))  # re-deliver evt_0003 (invoice.paid in_a1)
    return rows


def main() -> None:
    rows = build_rows()
    out = Path(__file__).parent / "bronze_stripe_events.csv"
    fields = list(rows[0].keys())
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
