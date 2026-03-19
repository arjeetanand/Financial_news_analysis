import json
from pathlib import Path

import pandas as pd

from mlops.artifacts import ArtifactRegistry
from mlops.contracts import DataContractValidator


def _valid_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Date_Time": "2026-03-10T10:00:00",
                "Headline": "TCS gains on upbeat guidance",
                "Summary": "Strong guidance improves outlook.",
                "Sentiment": "Positive",
                "Adjusted_Sentiment": "Positive",
                "Triggered_Stock_Symbols": "TCS",
            }
        ]
    )


def test_data_contract_validator_accepts_valid_frame():
    validator = DataContractValidator()
    result = validator.validate(_valid_df())

    assert result.is_valid is True
    assert result.errors == []


def test_data_contract_validator_rejects_invalid_sentiment():
    validator = DataContractValidator()
    frame = _valid_df()
    frame.loc[0, "Sentiment"] = "Very Positive"

    result = validator.validate(frame)

    assert result.is_valid is False
    assert any("Unsupported Sentiment" in error for error in result.errors)


def test_artifact_registry_writes_record(tmp_path: Path):
    output_file = tmp_path / "updated_final.csv"
    _valid_df().to_csv(output_file, index=False)

    registry_path = tmp_path / "registry.json"
    registry = ArtifactRegistry(registry_path)
    record = registry.register(output_file)

    assert record.name == "updated_final.csv"
    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    assert len(saved["artifacts"]) == 1
    assert saved["artifacts"][0]["sha256"]
