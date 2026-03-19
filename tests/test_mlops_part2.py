from pathlib import Path

import pandas as pd

from mlops.drift import detect_sentiment_drift, population_stability_index
from mlops.experiments import ExperimentTracker


def test_population_stability_index_increases_with_distribution_shift():
    baseline = pd.Series(["Positive"] * 80 + ["Negative"] * 10 + ["Neutral"] * 10)
    current = pd.Series(["Positive"] * 20 + ["Negative"] * 70 + ["Neutral"] * 10)

    psi = population_stability_index(baseline, current)

    assert psi > 0.2


def test_detect_sentiment_drift_flags_shift_at_threshold():
    baseline = pd.Series(["Positive"] * 90 + ["Negative"] * 10)
    current = pd.Series(["Negative"] * 90 + ["Positive"] * 10)

    report = detect_sentiment_drift(baseline, current, threshold=0.2)

    assert report.is_drifted is True
    assert report.psi >= 0.2


def test_experiment_tracker_logs_and_reads_runs(tmp_path: Path):
    tracking_file = tmp_path / "experiments.jsonl"
    tracker = ExperimentTracker(tracking_file)

    run = tracker.log_run(
        dataset_path="/tmp/updated_final.xlsx",
        model_name="yiyanghkust/finbert-tone",
        parameters={"batch_size": 8},
        metrics={"f1": 0.74},
        notes="test run",
    )

    loaded_runs = tracker.load_runs()

    assert run.run_id
    assert len(loaded_runs) == 1
    assert loaded_runs[0].metrics["f1"] == 0.74
