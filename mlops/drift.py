from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class DriftReport:
    psi: float
    is_drifted: bool
    threshold: float


def population_stability_index(
    baseline: pd.Series,
    current: pd.Series,
    *,
    epsilon: float = 1e-8,
) -> float:
    """Compute PSI for two categorical distributions."""
    baseline_dist = (
        baseline.dropna().astype(str).str.lower().value_counts(normalize=True)
    )
    current_dist = (
        current.dropna().astype(str).str.lower().value_counts(normalize=True)
    )

    all_labels = sorted(set(baseline_dist.index).union(set(current_dist.index)))

    psi = 0.0
    for label in all_labels:
        base = float(baseline_dist.get(label, 0.0)) + epsilon
        curr = float(current_dist.get(label, 0.0)) + epsilon
        psi += (curr - base) * np.log(curr / base)

    return float(psi)


def detect_sentiment_drift(
    baseline: pd.Series,
    current: pd.Series,
    *,
    threshold: float = 0.2,
) -> DriftReport:
    psi = population_stability_index(baseline, current)
    return DriftReport(psi=psi, is_drifted=psi >= threshold, threshold=threshold)
