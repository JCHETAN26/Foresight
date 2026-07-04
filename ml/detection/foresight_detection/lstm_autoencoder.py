"""LSTM autoencoder for temporal anomaly detection.

Learns to reconstruct short windows of the multivariate metric series. High
reconstruction error on a window signals that the recent temporal pattern
departs from the learned per-tenant baseline — the temporal complement to
IsolationForest's point-outlier view.
"""

from __future__ import annotations

import numpy as np
import torch
from torch import nn


class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features: int, hidden_size: int = 32, latent_size: int = 16) -> None:
        super().__init__()
        self.encoder = nn.LSTM(n_features, hidden_size, batch_first=True)
        self.to_latent = nn.Linear(hidden_size, latent_size)
        self.from_latent = nn.Linear(latent_size, hidden_size)
        self.decoder = nn.LSTM(hidden_size, hidden_size, batch_first=True)
        self.output = nn.Linear(hidden_size, n_features)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq, features)
        _, (h, _) = self.encoder(x)
        latent = self.to_latent(h[-1])  # (batch, latent)
        seq_len = x.size(1)
        dec_in = self.from_latent(latent).unsqueeze(1).repeat(1, seq_len, 1)
        dec_out, _ = self.decoder(dec_in)
        return self.output(dec_out)


def make_windows(series: np.ndarray, window: int) -> np.ndarray:
    """Sliding windows over a (n_days, n_features) array → (n_windows, window, n_features)."""
    if len(series) < window:
        return np.empty((0, window, series.shape[1]), dtype=np.float32)
    return np.stack(
        [series[i : i + window] for i in range(len(series) - window + 1)]
    ).astype(np.float32)


def train_autoencoder(
    windows: np.ndarray,
    n_features: int,
    *,
    hidden_size: int = 32,
    latent_size: int = 16,
    epochs: int = 30,
    lr: float = 1e-2,
    seed: int = 0,
) -> LSTMAutoencoder:
    """Train the autoencoder on (mostly-normal) windows via reconstruction MSE."""
    torch.manual_seed(seed)
    model = LSTMAutoencoder(n_features, hidden_size, latent_size)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()
    x = torch.from_numpy(windows)

    model.train()
    for _ in range(epochs):
        opt.zero_grad()
        recon = model(x)
        loss = loss_fn(recon, x)
        loss.backward()
        opt.step()
    return model


def reconstruction_error(model: LSTMAutoencoder, windows: np.ndarray) -> np.ndarray:
    """Per-window mean squared reconstruction error."""
    if len(windows) == 0:
        return np.empty(0, dtype=np.float32)
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(windows.astype(np.float32))
        recon = model(x)
        err = ((recon - x) ** 2).mean(dim=(1, 2))
    return err.numpy()
