"""Foresight detection worker — runs the ML + agent pipeline over the KPI store.

Reads kpi_daily from Postgres, runs detection + classification + the grounded
agent (real Claude), and upserts the results into anomaly_log. This is the
compute half of the backend: the anomaly_log the API serves is the genuine
output of the pipeline, not a preloaded bundle.
"""

__version__ = "0.1.0"
