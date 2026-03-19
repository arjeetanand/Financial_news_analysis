from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mlops.artifacts import ArtifactRegistry
from mlops.business_value import event_study_backtest, sentiment_calibration_table
from mlops.contracts import DataContractValidator
from mlops.drift import detect_sentiment_drift
from mlops.entity_linking import evaluate_entity_linking
from mlops.experiments import ExperimentTracker


def _load_dataset(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {path.suffix}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Part 1/2/3/4 productionization CLI: validate, register artifacts, "
            "track experiments, detect drift, evaluate entity linking, and run event-study backtests."
        )
    )
    parser.add_argument("--input", required=True, help="Path to pipeline output data file")
    parser.add_argument(
        "--registry",
        default="artifacts/registry.json",
        help="Where to store artifact metadata",
    )
    parser.add_argument(
        "--lineage",
        default="artifacts/lineage.json",
        help="Where to write lineage metadata",
    )
    parser.add_argument(
        "--track-experiment",
        action="store_true",
        help="Track this run as an experiment in artifacts/experiments.jsonl",
    )
    parser.add_argument(
        "--model-name",
        default="yiyanghkust/finbert-tone",
        help="Model name to record when --track-experiment is enabled",
    )
    parser.add_argument(
        "--baseline",
        help="Optional baseline dataset path for sentiment drift detection",
    )
    parser.add_argument(
        "--drift-threshold",
        type=float,
        default=0.2,
        help="PSI threshold for drift detection",
    )
    parser.add_argument(
        "--entity-labels",
        help="Optional labeled dataset path with true stock symbols for entity-linking accuracy evaluation.",
    )
    parser.add_argument(
        "--pred-col",
        default="Triggered_Stock_Symbols",
        help="Prediction column in --input for entity-linking evaluation",
    )
    parser.add_argument(
        "--label-col",
        default="Triggered_Stock_Symbols",
        help="Label column in --entity-labels for entity-linking evaluation",
    )
    parser.add_argument(
        "--run-backtest",
        action="store_true",
        help="Run event-study style backtest metrics using sentiment and forward return columns.",
    )
    parser.add_argument(
        "--sentiment-col",
        default="Sentiment",
        help="Sentiment column for drift/backtest logic.",
    )
    parser.add_argument(
        "--entry-price-col",
        default="News_day",
        help="Entry price column for forward-return backtest.",
    )
    parser.add_argument(
        "--exit-price-col",
        default="News_Day_After",
        help="Exit price column for forward-return backtest.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    df = _load_dataset(input_path)

    validator = DataContractValidator()
    result = validator.validate(df)

    print("Validation result:")
    print(
        json.dumps(
            {
                "is_valid": result.is_valid,
                "errors": result.errors,
                "warnings": result.warnings,
            },
            indent=2,
        )
    )

    if not result.is_valid:
        return 1

    registry = ArtifactRegistry(args.registry)
    record = registry.register(input_path)

    lineage_path = Path(args.lineage)
    lineage_path.parent.mkdir(parents=True, exist_ok=True)
    lineage = {
        "dataset": str(input_path.resolve()),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "artifact": record.__dict__,
    }

    if args.baseline:
        baseline_df = _load_dataset(Path(args.baseline))
        drift_report = detect_sentiment_drift(
            baseline_df[args.sentiment_col],
            df[args.sentiment_col],
            threshold=args.drift_threshold,
        )
        lineage["sentiment_drift"] = drift_report.__dict__
        print("Drift report:")
        print(json.dumps(drift_report.__dict__, indent=2))

    if args.entity_labels:
        labels_df = _load_dataset(Path(args.entity_labels))
        eval_metrics = evaluate_entity_linking(df[args.pred_col], labels_df[args.label_col])
        lineage["entity_linking_metrics"] = eval_metrics
        print("Entity linking metrics:")
        print(json.dumps(eval_metrics, indent=2))

    if args.run_backtest:
        report = event_study_backtest(
            df,
            sentiment_col=args.sentiment_col,
            entry_price_col=args.entry_price_col,
            exit_price_col=args.exit_price_col,
        )
        calibration = sentiment_calibration_table(
            df,
            sentiment_col=args.sentiment_col,
            entry_price_col=args.entry_price_col,
            exit_price_col=args.exit_price_col,
        )

        lineage["event_study_backtest"] = report.__dict__
        lineage["sentiment_calibration"] = calibration.to_dict(orient="records")

        print("Event-study backtest:")
        print(json.dumps(report.__dict__, indent=2))
        print("Sentiment calibration:")
        print(json.dumps(lineage["sentiment_calibration"], indent=2))

    if args.track_experiment:
        tracker = ExperimentTracker()
        metrics = {
            "row_count": float(len(df)),
            "warning_count": float(len(result.warnings)),
            "drift_psi": float(lineage.get("sentiment_drift", {}).get("psi", 0.0)),
            "entity_accuracy": float(lineage.get("entity_linking_metrics", {}).get("accuracy", 0.0)),
            "backtest_hit_rate": float(lineage.get("event_study_backtest", {}).get("hit_rate", 0.0)),
            "backtest_sharpe_like": float(
                lineage.get("event_study_backtest", {}).get("strategy_sharpe_like", 0.0)
            ),
        }
        run = tracker.log_run(
            dataset_path=str(input_path.resolve()),
            model_name=args.model_name,
            parameters={
                "drift_threshold": args.drift_threshold,
                "entry_price_col": args.entry_price_col,
                "exit_price_col": args.exit_price_col,
            },
            metrics=metrics,
            notes="Automated run from pipeline_cli",
        )
        lineage["experiment_run"] = run.__dict__
        print(f"Experiment run tracked: {run.run_id}")

    lineage_path.write_text(json.dumps(lineage, indent=2), encoding="utf-8")

    print(f"Registered artifact: {record.name}")
    print(f"Lineage written to: {lineage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
