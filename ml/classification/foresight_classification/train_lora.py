"""LoRA fine-tuning of T5-small for anomaly-type classification.

Frames classification as text-to-text: input the anomaly description, generate
the type label. LoRA (PEFT) trains only a small set of adapter weights on top of
the frozen T5-small, so it fits on CPU / a consumer GPU.
"""

from __future__ import annotations

import pandas as pd
import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch.utils.data import DataLoader, Dataset
from transformers import T5ForConditionalGeneration, T5TokenizerFast

PREFIX = "classify anomaly type: "


class _LabelDataset(Dataset):
    def __init__(self, df: pd.DataFrame, tok: T5TokenizerFast, max_in: int = 64, max_out: int = 8):
        self.texts = [PREFIX + t for t in df["text"].tolist()]
        self.labels = df["label"].tolist()
        self.tok, self.max_in, self.max_out = tok, max_in, max_out

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, i: int):
        x = self.tok(
            self.texts[i], max_length=self.max_in, truncation=True,
            padding="max_length", return_tensors="pt",
        )
        y = self.tok(
            self.labels[i], max_length=self.max_out, truncation=True,
            padding="max_length", return_tensors="pt",
        )
        labels = y.input_ids.squeeze(0)
        labels[labels == self.tok.pad_token_id] = -100  # ignore pad in loss
        return x.input_ids.squeeze(0), x.attention_mask.squeeze(0), labels


def train_lora(
    train_df: pd.DataFrame,
    output_dir: str,
    *,
    base: str = "t5-small",
    epochs: int = 3,
    lr: float = 1e-3,
    batch_size: int = 16,
    seed: int = 0,
) -> str:
    """Fine-tune and save the LoRA adapter + tokenizer to `output_dir`."""
    torch.manual_seed(seed)
    tok = T5TokenizerFast.from_pretrained(base)
    model = T5ForConditionalGeneration.from_pretrained(base)

    peft_cfg = LoraConfig(
        task_type=TaskType.SEQ_2_SEQ_LM,
        r=8,
        lora_alpha=16,
        target_modules=["q", "v"],
        lora_dropout=0.05,
    )
    model = get_peft_model(model, peft_cfg)

    loader = DataLoader(_LabelDataset(train_df, tok), batch_size=batch_size, shuffle=True)
    opt = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=lr)

    model.train()
    for _ in range(epochs):
        for ids, mask, labels in loader:
            opt.zero_grad()
            loss = model(input_ids=ids, attention_mask=mask, labels=labels).loss
            loss.backward()
            opt.step()

    model.save_pretrained(output_dir)
    tok.save_pretrained(output_dir)
    return output_dir
