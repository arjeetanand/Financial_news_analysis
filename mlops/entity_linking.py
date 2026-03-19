from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

import pandas as pd


def normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", str(value).upper())
    return re.sub(r"\s+", " ", cleaned).strip()


@dataclass
class EntityMatch:
    company: str
    symbol: str
    score: float


class EntityLinker:
    """Rule + fuzzy entity linker for headline/summary to stock symbols."""

    def __init__(
        self,
        company_to_symbol: dict[str, str],
        aliases: dict[str, str] | None = None,
        fuzzy_threshold: float = 0.86,
    ) -> None:
        self.fuzzy_threshold = fuzzy_threshold
        self.aliases = {normalize_text(k): normalize_text(v) for k, v in (aliases or {}).items()}

        self.company_to_symbol: dict[str, str] = {
            normalize_text(company): symbol.upper()
            for company, symbol in company_to_symbol.items()
            if isinstance(company, str) and isinstance(symbol, str)
        }
        self._keys = list(self.company_to_symbol.keys())

    def link_text(self, text: str) -> list[EntityMatch]:
        normalized_text = normalize_text(text)
        if not normalized_text:
            return []

        expanded_text = self._expand_aliases(normalized_text)
        matches: list[EntityMatch] = []

        # exact/substring matches first
        for company in self._keys:
            symbol = self.company_to_symbol[company]
            if company in expanded_text or f" {symbol} " in f" {expanded_text} ":
                matches.append(EntityMatch(company=company, symbol=symbol, score=1.0))

        if matches:
            return self._dedupe(matches)

        # fuzzy fallback
        for company in self._keys:
            score = SequenceMatcher(None, company, expanded_text).ratio()
            if score >= self.fuzzy_threshold:
                matches.append(
                    EntityMatch(company=company, symbol=self.company_to_symbol[company], score=float(score))
                )

        return self._dedupe(sorted(matches, key=lambda item: item.score, reverse=True))

    def link_dataframe(
        self,
        df: pd.DataFrame,
        *,
        headline_col: str = "Headline",
        summary_col: str = "Summary",
    ) -> pd.DataFrame:
        output = df.copy()

        def _link_row(row: pd.Series) -> tuple[str | None, str | None, float | None]:
            text = f"{row.get(headline_col, '')} {row.get(summary_col, '')}".strip()
            results = self.link_text(text)
            if not results:
                return None, None, None

            names = ", ".join([m.company for m in results])
            symbols = ", ".join([m.symbol for m in results])
            best_score = max(m.score for m in results)
            return names, symbols, best_score

        output[["Linked_Company_Names", "Linked_Symbols", "Entity_Link_Score"]] = output.apply(
            lambda row: pd.Series(_link_row(row)),
            axis=1,
        )
        return output

    def _expand_aliases(self, text: str) -> str:
        expanded = text
        for alias, canonical in self.aliases.items():
            expanded = expanded.replace(alias, canonical)
        return expanded

    @staticmethod
    def _dedupe(matches: list[EntityMatch]) -> list[EntityMatch]:
        seen: set[tuple[str, str]] = set()
        unique: list[EntityMatch] = []
        for item in matches:
            key = (item.company, item.symbol)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique


def evaluate_entity_linking(
    predictions: pd.Series,
    labels: pd.Series,
) -> dict[str, float]:
    pred = predictions.fillna("").astype(str).str.upper().str.strip()
    gold = labels.fillna("").astype(str).str.upper().str.strip()

    total = len(gold)
    if total == 0:
        return {"accuracy": 0.0}

    correct = int((pred == gold).sum())
    return {"accuracy": correct / total}
