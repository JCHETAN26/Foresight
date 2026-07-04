"""Inference wrapper for the LoRA-fine-tuned T5 anomaly classifier."""

from __future__ import annotations

import torch
from peft import PeftModel
from transformers import T5ForConditionalGeneration, T5TokenizerFast

from foresight_classification import LABELS
from foresight_classification.train_lora import PREFIX


def _closest_label(raw: str) -> str:
    """Map a generated string to a valid label (exact, else best token overlap)."""
    raw = raw.strip().lower().replace(" ", "_")
    if raw in LABELS:
        return raw
    raw_tokens = set(raw.replace("_", " ").split())
    best, best_overlap = LABELS[0], -1
    for label in LABELS:
        overlap = len(raw_tokens & set(label.split("_")))
        if overlap > best_overlap:
            best, best_overlap = label, overlap
    return best


class T5Classifier:
    def __init__(self, model: torch.nn.Module, tok: T5TokenizerFast) -> None:
        self.model = model
        self.tok = tok

    @classmethod
    def from_pretrained(cls, adapter_dir: str, base: str = "t5-small") -> T5Classifier:
        tok = T5TokenizerFast.from_pretrained(adapter_dir)
        base_model = T5ForConditionalGeneration.from_pretrained(base)
        model = PeftModel.from_pretrained(base_model, adapter_dir)
        model.eval()
        return cls(model, tok)

    def predict(self, texts: list[str], batch_size: int = 32) -> list[str]:
        preds: list[str] = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                batch = [PREFIX + t for t in texts[start : start + batch_size]]
                enc = self.tok(
                    batch, return_tensors="pt", truncation=True, max_length=64, padding=True
                )
                out = self.model.generate(**enc, max_new_tokens=8)
                decoded = self.tok.batch_decode(out, skip_special_tokens=True)
                preds.extend(_closest_label(d) for d in decoded)
        return preds
