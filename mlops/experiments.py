from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class ExperimentRun:
    run_id: str
    created_at_utc: str
    dataset_path: str
    model_name: str
    parameters: dict[str, Any]
    metrics: dict[str, float]
    notes: str = ""


class ExperimentTracker:
    """Tiny open-source experiment tracker backed by JSONL files."""

    def __init__(self, tracking_file: Path | str = "artifacts/experiments.jsonl") -> None:
        self.tracking_file = Path(tracking_file)
        self.tracking_file.parent.mkdir(parents=True, exist_ok=True)

    def log_run(
        self,
        *,
        dataset_path: str,
        model_name: str,
        parameters: dict[str, Any],
        metrics: dict[str, float],
        notes: str = "",
    ) -> ExperimentRun:
        run = ExperimentRun(
            run_id=self._build_run_id(model_name),
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            dataset_path=dataset_path,
            model_name=model_name,
            parameters=parameters,
            metrics=metrics,
            notes=notes,
        )
        with self.tracking_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(run)) + "\n")
        return run

    def load_runs(self) -> list[ExperimentRun]:
        if not self.tracking_file.exists():
            return []

        runs: list[ExperimentRun] = []
        with self.tracking_file.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                if not raw_line.strip():
                    continue
                payload = json.loads(raw_line)
                runs.append(ExperimentRun(**payload))
        return runs

    @staticmethod
    def _build_run_id(model_name: str) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        safe_model_name = model_name.replace("/", "-").replace(" ", "-").lower()
        return f"{safe_model_name}-{timestamp}"
