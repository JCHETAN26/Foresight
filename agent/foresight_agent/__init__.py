"""Foresight agent — LangGraph pipeline that turns an anomaly into a grounded,
alertable explanation.

    detect → classify → retrieve → reason → evaluate → alert

`reason` calls Claude; `evaluate` gates on faithfulness so a hallucinated
explanation is never alerted. The LLM and the retriever are pluggable so the
graph runs in CI with no API key and no network.
"""

__version__ = "0.1.0"
