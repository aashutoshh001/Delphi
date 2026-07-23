"""JSON-file-backed InsightPackageRepository — mirrors hypothesis_agent's
JsonHypothesisStore: no in-process cache, read fresh + atomic write-then-
rename on every call, safe for multiple instances pointed at the same path."""

from __future__ import annotations

import json
from pathlib import Path

from insight_pipeline.contracts.insight_package import InsightPackage
from insight_pipeline.ports.insight_package_repository import InsightPackageRepository


class JsonInsightStore(InsightPackageRepository):
    def __init__(self, file_path: Path | str) -> None:
        self._path = Path(file_path)

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        text = self._path.read_text().strip()
        return json.loads(text) if text else []

    def _write(self, entries: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False, default=str))
        tmp_path.replace(self._path)

    async def save(self, package: InsightPackage) -> None:
        entries = self._read()
        entries.append(json.loads(package.model_dump_json()))
        self._write(entries)

    async def get(self, package_id: str) -> InsightPackage | None:
        for entry in self._read():
            if entry.get("id") == package_id:
                return InsightPackage.model_validate(entry)
        return None

    async def list_recent(self, limit: int = 20) -> list[InsightPackage]:
        entries = self._read()
        entries.sort(key=lambda e: e.get("generated_at", ""), reverse=True)
        return [InsightPackage.model_validate(e) for e in entries[:limit]]
