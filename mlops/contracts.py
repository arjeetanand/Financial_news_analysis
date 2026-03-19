from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


REQUIRED_COLUMNS = {
    "Date_Time",
    "Headline",
    "Summary",
    "Sentiment",
    "Adjusted_Sentiment",
    "Triggered_Stock_Symbols",
}

ALLOWED_SENTIMENTS = {"positive", "negative", "neutral"}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class DataContractValidator:
    """Lightweight, open-source friendly data contract checks for pipeline outputs."""

    def __init__(self, required_columns: Iterable[str] | None = None) -> None:
        self.required_columns = set(required_columns or REQUIRED_COLUMNS)

    def validate(self, df: pd.DataFrame) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        missing_columns = sorted(self.required_columns - set(df.columns))
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")

        if "Sentiment" in df.columns:
            invalid_sentiments = self._find_invalid_sentiments(df["Sentiment"])
            if invalid_sentiments:
                errors.append(
                    "Unsupported Sentiment labels found: "
                    + ", ".join(sorted(invalid_sentiments))
                )

        if "Adjusted_Sentiment" in df.columns:
            invalid_adjusted = self._find_invalid_sentiments(df["Adjusted_Sentiment"])
            if invalid_adjusted:
                errors.append(
                    "Unsupported Adjusted_Sentiment labels found: "
                    + ", ".join(sorted(invalid_adjusted))
                )

        if {"Headline", "Date_Time"}.issubset(df.columns):
            duplicate_count = int(df.duplicated(subset=["Headline", "Date_Time"]).sum())
            if duplicate_count:
                warnings.append(
                    f"Found {duplicate_count} duplicate rows by (Headline, Date_Time)."
                )

        if "Triggered_Stock_Symbols" in df.columns:
            empty_symbols = int(df["Triggered_Stock_Symbols"].fillna("").eq("").sum())
            if empty_symbols:
                warnings.append(
                    f"Found {empty_symbols} rows without Triggered_Stock_Symbols."
                )

        return ValidationResult(is_valid=not errors, errors=errors, warnings=warnings)

    @staticmethod
    def _find_invalid_sentiments(series: pd.Series) -> set[str]:
        normalized = series.dropna().astype(str).str.strip().str.lower()
        return set(normalized.unique()) - ALLOWED_SENTIMENTS
