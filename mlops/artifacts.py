from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ArtifactRecord:
    name: str
    path: str
    sha256: str
    size_bytes: int
    created_at_utc: str


class ArtifactRegistry:
    """Simple local artifact registry for lineage + reproducibility."""

    def __init__(self, registry_path: Path | str = "artifacts/registry.json") -> None:
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

    def register(self, artifact_path: Path | str, name: str | None = None) -> ArtifactRecord:
        artifact = Path(artifact_path)
        if not artifact.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact}")

        record = ArtifactRecord(
            name=name or artifact.name,
            path=str(artifact.resolve()),
            sha256=self._sha256(artifact),
            size_bytes=artifact.stat().st_size,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        payload = self._load_registry()
        payload.setdefault("artifacts", []).append(asdict(record))
        self.registry_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return record

    def _load_registry(self) -> dict:
        if not self.registry_path.exists():
            return {"artifacts": []}
        return json.loads(self.registry_path.read_text(encoding="utf-8"))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
