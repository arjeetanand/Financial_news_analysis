from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from mlops.artifacts import ArtifactRegistry
from mlops.contracts import DataContractValidator


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
        description="Part 1 (Productionization): validate outputs and register artifacts."
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
    args = parser.parse_args()

    input_path = Path(args.input)
    df = _load_dataset(input_path)

    validator = DataContractValidator()
    result = validator.validate(df)

    print("Validation result:")
    print(json.dumps({"is_valid": result.is_valid, "errors": result.errors, "warnings": result.warnings}, indent=2))

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
    lineage_path.write_text(json.dumps(lineage, indent=2), encoding="utf-8")

    print(f"Registered artifact: {record.name}")
    print(f"Lineage written to: {lineage_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
