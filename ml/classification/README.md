# Foresight — Anomaly Classification (M2)

Given a detected anomaly's description, name its **type** — one of
`payment_failure`, `churn_spike`, `seasonal_dip`, `acquisition_drop`,
`pricing_effect`, `infrastructure_issue` — so an alert can say *what* happened,
not just *that* something did. This label routes the agent's explanation (M3).

## Approach

- **Text-to-text**: input the anomaly description, generate the label.
- **LoRA fine-tune of T5-small** (PEFT): trains a small adapter on the frozen
  60M-param base — fits on CPU / a consumer GPU.
- **Baseline**: TF-IDF + logistic regression — a strong, cheap bar the T5 has to
  clear to justify its cost.
- Dataset: templated anomaly descriptions with deliberate cross-class vocabulary
  overlap, so the task is learned rather than keyword-matched.

## Measured results

**Template-holdout** test (the test set uses phrasings *never seen in
training*), T5 trained 12 epochs to convergence. Measured, not asserted:

| Model | Accuracy | Macro-F1 | Weighted-F1 |
|---|---|---|---|
| **TF-IDF + LogReg** | **0.835** | 0.748 | **0.801** |
| LoRA T5-small | 0.747 | 0.747 | 0.714 |

### What the numbers actually say

- **The TF-IDF baseline matches or beats the fine-tuned T5** on unseen phrasings:
  higher accuracy and weighted-F1, dead-level on macro-F1 (0.748 vs 0.747).
- More training helped the T5 a lot (accuracy 0.65 → 0.75 from 4 → 12 epochs) and
  it reaches macro-F1 parity — so the LoRA fine-tuning **works and generalizes** —
  but it buys **no accuracy advantage** over a model that is ~100× cheaper to
  serve.
- **Engineering conclusion: ship the TF-IDF classifier for this task.** Anomaly
  descriptions are structured and lexically separable; a fine-tuned transformer
  is not justified here. (An earlier same-template split had *both* models at
  100% — the honest signal only appears under template holdout.)
- The plan's "fine-tuned T5 beats GPT-4o zero-shot by 18%" is **not supported**:
  a linear baseline already matches the T5, so the task does not need a
  fine-tuned LLM at all. The GPT-4o comparison (needs Azure OpenAI) was not run.

The LoRA pipeline is kept because it is validated and reusable for a genuinely
harder, free-text problem — the M3 chat ("why did my MRR drop last Tuesday?") —
where semantic understanding matters. It just isn't the right tool for *this*
classification task.

Regenerate: `python -m foresight_classification.train --epochs 12`
(writes `outputs/classification_benchmark.csv`).

## Run it

```bash
cd ml/classification
pip install -e ".[t5,dev]"          # base install (sklearn) is enough for the baseline
pytest -q                            # fast: data + baseline (T5 test gated off)
FORESIGHT_RUN_T5=1 pytest -q         # include the T5 end-to-end test (downloads t5-small)
python -m foresight_classification.train --epochs 3
```
