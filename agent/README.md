# Foresight — Agent (M3)

The LangGraph pipeline that turns an `AnomalyRecord` (from `ml/anomaly`) into a
grounded, alertable explanation — the second half of the product loop.

```
detect → classify → retrieve → reason → evaluate → alert
                        ▲__________________│  (retry with more context
                                              if faithfulness < 0.85)
```

| Node | What it does |
|---|---|
| **detect** | Receives the anomaly event. |
| **classify** | Surfaces the type + confidence (from the M2 classifier). |
| **retrieve** | Freshness-aware hybrid RAG (below). |
| **reason** | Claude generates a grounded explanation from record + context. |
| **evaluate** | Faithfulness gate — a hallucinated number blocks the alert. |
| **alert** | Formats a Slack message; withholds low-confidence / low-faithfulness alerts. |

## Retrieval (`retrieval.py`)

- **Qdrant in-memory** (`:memory:` — real Qdrant, no server) for dense search,
  **BM25** for sparse, blended with **reciprocal rank fusion**.
- **Freshness weighting**: documents from the last 15 minutes get a **3× weight**
  in the RRF score, so current operational context (a deploy, a price change)
  outranks stale reference docs.
- Dense embeddings use a deterministic **hashing vectorizer** so the graph runs
  in CI with no model download; `BAAI/bge-small-en` is the production swap (the
  `Embedder` seam).

## Grounding & safety

- **Faithfulness gate** (`faithfulness.py`): every number in the explanation must
  trace to the record or retrieved context; otherwise the alert is held. This is
  the deterministic hard floor that pairs with an LLM-as-judge (LangSmith) in
  production.
- **Human-in-the-loop**: anomalies with type confidence < 0.6 are withheld
  (`status: held_for_review`) rather than alerted.

## Provider-agnostic generation (`llm.py`)

`ClaudeGenerator` calls Claude (Opus 4.8) via the Anthropic SDK; `StubGenerator`
composes a grounded explanation deterministically for CI. Azure OpenAI (the
plan's primary) is a drop-in third `Generator`.

## Honest notes

- **Freshness can beat relevance.** On the sample `payment_failure` anomaly, the
  two recent events (a price change and an outage, 8–12 min old) outrank the
  payment-failure runbook purely on the 3× boost. That is the freshness
  mechanism working as specified — but it's a real recency/relevance tradeoff,
  and the next refinement is to boost recent docs only when they also clear a
  relevance floor.
- The hashing embedder is weaker than a trained sentence encoder; retrieval
  quality improves materially with `bge-small`.
- Faithfulness here is *numeric* grounding — necessary, not sufficient. Semantic
  faithfulness needs the LLM-judge pass (LangSmith), which is keyed on
  `ANTHROPIC_API_KEY` and not run in CI.

## Run it

```bash
cd agent
pip install -e ".[llm,dev]"
pytest -q                                   # stub generator — no key needed
python -m foresight_agent.run               # stub
ANTHROPIC_API_KEY=... python -m foresight_agent.run --live   # real Claude
```
