"""JSON-file-backed store for subject-matter-expert feedback on insights.

Mirrors JsonInsightStore's read-fresh + atomic tmp-write-then-replace pattern,
but adds an asyncio.Lock because feedback is a read-modify-write append (unlike
the append-only JsonInsightStore.save, concurrent writers could otherwise lose
entries). Demo-grade storage: one flat JSON list at sample_data/insight_feedback.json.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonInsightFeedbackStore:
    def __init__(self, file_path: Path | str) -> None:
        self._path = Path(file_path)
        self._lock = asyncio.Lock()

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        text = self._path.read_text().strip()
        return json.loads(text) if text else []

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False, default=str))
        tmp_path.replace(self._path)

    async def add(self, insight_id: str, feedback: str) -> dict[str, Any]:
        entry = {
            "insight_id": insight_id,
            "feedback": feedback,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        async with self._lock:
            entries = self._read()
            entries.append(entry)
            self._write(entries)
        return entry

    async def list_for(self, insight_id: str) -> list[dict[str, Any]]:
        return [e for e in self._read() if e.get("insight_id") == insight_id]
