"""Training + tuning driver: Optuna sweep, W&B tracking, benchmark report.

Splits tenants into tune/holdout, uses Optuna to maximize PR-AUC on the tune
split, then reports the final benchmark on the untouched holdout split. All runs
are logged to Weights & Biases (offline mode by default — no account needed to
produce the run artifacts; set WANDB_MODE=online with an API key to sync).

    python -m foresight_detection.train --trials 20
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

from foresight_detection.benchmark import evaluate, run_benchmark
from foresight_detection.data import DatasetConfig, generate
from foresight_detection.ensemble import DetectionEnsemble, EnsembleConfig


def _split_by_tenant(df, holdout_frac: float = 0.33, seed: int = 0):
    tenants = np.array(sorted(df["tenant_id"].unique()))
    rng = np.random.default_rng(seed)
    rng.shuffle(tenants)
    n_holdout = max(1, int(len(tenants) * holdout_frac))
    holdout = set(tenants[:n_holdout])
    tune = df[~df["tenant_id"].isin(holdout)].copy()
    hold = df[df["tenant_id"].isin(holdout)].copy()
    return tune, hold


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--out", default="outputs")
    args = parser.parse_args(argv)

    os.environ.setdefault("WANDB_MODE", "offline")
    os.environ.setdefault("WANDB_SILENT", "true")
    import optuna
    import wandb

    df = generate(DatasetConfig())
    tune_df, holdout_df = _split_by_tenant(df)
    tune_labels = tune_df.sort_values(["tenant_id", "day"])["is_anomaly"].to_numpy()

    run = wandb.init(project="foresight-detection", job_type="sweep", reinit=True)

    def objective(trial: optuna.Trial) -> float:
        cfg = EnsembleConfig(
            window=trial.suggest_int("window", 5, 10),
            hidden_size=trial.suggest_categorical("hidden_size", [16, 32, 64]),
            lstm_weight=trial.suggest_float("lstm_weight", 0.2, 0.8),
            contamination=trial.suggest_float("contamination", 0.03, 0.08),
            epochs=args.epochs,
            seed=0,
        )
        scores = DetectionEnsemble(cfg).fit_score(
            tune_df.sort_values(["tenant_id", "day"]).reset_index(drop=True)
        )
        m = evaluate(scores, tune_labels)
        wandb.log({"trial": trial.number, "tune_pr_auc": m["pr_auc"], "tune_f1": m["f1"]})
        return m["pr_auc"]

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=args.trials, show_progress_bar=False)

    best = EnsembleConfig(epochs=args.epochs, **study.best_params)
    table = run_benchmark(holdout_df, ensemble_config=best)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "best_params.json").write_text(json.dumps(study.best_params, indent=2))
    table.to_csv(out / "benchmark.csv", index=False)

    wandb.log({"best_params": study.best_params})
    wandb.log({"holdout_benchmark": wandb.Table(dataframe=table)})
    run.finish()

    print("Best params:", study.best_params)
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
