"""JSON-file-backed store that doubles as both HistoricalMemoryRepository
and FeedbackRepository, matching the schema the existing static frontend
(sample_data/stories.json) already expects — extended with the fields a
hypothesis needs (lens, scorecard, critique, ...) and a tri-state `reaction`.

No in-process cache: every call reads the file fresh and every mutation
writes the whole file back atomically, so multiple instances (or multiple
server workers) pointed at the same path stay consistent without a shared
cache. Embeddings for existing entries are recomputed on the fly rather than
persisted, to keep the human/frontend-facing JSON free of vector blobs —
fine at the file sizes this is meant for; a real deployment would cache
them."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hypothesis_agent.adapters.rendering.card_image_renderer import render_card_image
from hypothesis_agent.adapters.rendering.detail_page_renderer import render_detail_page
from hypothesis_agent.contracts.hypothesis import (
    CritiqueResult,
    EvaluationScorecard,
    SearchStatistics,
)
from hypothesis_agent.contracts.memory import (
    FeedbackRecord,
    FeedbackSummary,
    HistoricalHypothesisRecord,
)
from hypothesis_agent.ports.embedding_service import EmbeddingService
from hypothesis_agent.ports.feedback_repository import FeedbackRepository
from hypothesis_agent.ports.historical_memory_repository import (
    HistoricalMemoryRepository,
)

REACTIONS = ("none", "up", "down")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JsonHypothesisStore(HistoricalMemoryRepository, FeedbackRepository):
    def __init__(
        self,
        file_path: Path | str,
        embedding_service: EmbeddingService,
        render_detail_pages: bool = True,
        detail_url_prefix: str = "sample_data/hypotheses",
        render_card_images: bool = True,
        card_image_url_prefix: str = "sample_data/card_images",
    ) -> None:
        self._path = Path(file_path)
        self._embedding_service = embedding_service
        self._render_detail_pages = render_detail_pages
        self._detail_url_prefix = detail_url_prefix
        self._render_card_images = render_card_images
        self._card_image_url_prefix = card_image_url_prefix
        self._lock = asyncio.Lock()

    # -- file I/O ----------------------------------------------------

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        text = self._path.read_text().strip()
        return json.loads(text) if text else []

    def _write(self, entries: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
        tmp_path.replace(self._path)

    # -- record <-> on-disk entry -------------------------------------

    def _record_to_entry(self, record: HistoricalHypothesisRecord) -> dict[str, Any]:
        # Deterministic per-hypothesis filename (the record's own id) — same
        # image every time this entry is reloaded, generated once at save()
        # time, never regenerated on the fly.
        image_url = f"{self._card_image_url_prefix}/{record.id}.svg" if self._render_card_images else ""
        return {
            "id": record.id,
            "imageURL": image_url,
            # Catchy headline / decent-length summary for the feed — the full
            # rigorous statement/mechanism live on the detail page, not here.
            # Fall back to the full text only if headline/summary is somehow
            # empty (e.g. a record built outside the normal finalize path).
            "title": record.headline or record.statement,
            "description": record.summary or record.mechanism,
            "readmoreURL": f"{self._detail_url_prefix}/{record.id}.html",
            "reaction": "none",
            "organization_id": record.organization_id,
            "lens": record.lens,
            "statement": record.statement,
            "mechanism": record.mechanism,
            "target_constructs": record.target_constructs,
            "scorecard": record.scorecard.model_dump(mode="json") if record.scorecard else None,
            "critique": record.critique.model_dump(mode="json") if record.critique else None,
            "search_stats": record.search_stats.model_dump(mode="json") if record.search_stats else None,
            "generated_at": record.created_at.isoformat(),
        }

    def _entry_to_record(
        self, entry: dict[str, Any], embedding: list[float] | None = None
    ) -> HistoricalHypothesisRecord:
        entry_id = entry.get("id") or hashlib.sha256(entry.get("title", "").encode()).hexdigest()[:16]
        created_at = (
            datetime.fromisoformat(entry["generated_at"]) if entry.get("generated_at") else _utcnow()
        )
        return HistoricalHypothesisRecord(
            id=entry_id,
            organization_id=entry.get("organization_id"),
            headline=entry.get("title", ""),
            summary=entry.get("description", ""),
            # Older entries (written before headline/summary existed) only
            # ever had the full statement/mechanism in title/description —
            # "statement"/"mechanism" keys are the authoritative full text
            # when present, falling back to title/description otherwise.
            statement=entry.get("statement") or entry.get("title", ""),
            mechanism=entry.get("mechanism") or entry.get("description", ""),
            lens=entry.get("lens") or "unknown",
            target_constructs=entry.get("target_constructs") or [],
            embedding=embedding,
            scorecard=EvaluationScorecard.model_validate(entry["scorecard"]) if entry.get("scorecard") else None,
            critique=CritiqueResult.model_validate(entry["critique"]) if entry.get("critique") else None,
            search_stats=SearchStatistics.model_validate(entry["search_stats"])
            if entry.get("search_stats")
            else None,
            created_at=created_at,
        )

    # -- HistoricalMemoryRepository ------------------------------------

    async def search_similar(
        self, embedding: list[float], organization_id: str | None, top_k: int = 5
    ) -> list[HistoricalHypothesisRecord]:
        entries = self._read()
        scored: list[tuple[float, dict[str, Any], list[float]]] = []
        for entry in entries:
            if organization_id is not None and entry.get("organization_id") not in (None, organization_id):
                continue
            # Compare against the full statement/mechanism, not the short
            # headline/summary teaser — candidate embeddings (generate_candidate.py)
            # are computed from the full text too, so this keeps the
            # similarity comparison apples-to-apples for the dedup guarantee.
            statement = entry.get("statement") or entry.get("title", "")
            mechanism = entry.get("mechanism") or entry.get("description", "")
            entry_embedding = await self._embedding_service.embed(f"{statement} {mechanism}")
            similarity = EmbeddingService.cosine_similarity(embedding, entry_embedding)
            scored.append((similarity, entry, entry_embedding))
        scored.sort(key=lambda triple: triple[0], reverse=True)
        return [
            self._entry_to_record(entry, embedding=entry_embedding)
            for _similarity, entry, entry_embedding in scored[:top_k]
        ]

    async def list_recent(
        self, organization_id: str | None, limit: int = 20
    ) -> list[HistoricalHypothesisRecord]:
        entries = self._read()
        filtered = [
            e
            for e in entries
            if organization_id is None or e.get("organization_id") in (None, organization_id)
        ]
        filtered.sort(key=lambda e: e.get("generated_at", ""), reverse=True)
        return [self._entry_to_record(e) for e in filtered[:limit]]

    async def save(self, record: HistoricalHypothesisRecord) -> None:
        async with self._lock:
            entries = self._read()
            entries.append(self._record_to_entry(record))
            self._write(entries)
        if self._render_detail_pages:
            detail_dir = self._path.parent / "hypotheses"
            detail_dir.mkdir(parents=True, exist_ok=True)
            (detail_dir / f"{record.id}.html").write_text(render_detail_page(record))
        if self._render_card_images:
            image_dir = self._path.parent / "card_images"
            image_dir.mkdir(parents=True, exist_ok=True)
            (image_dir / f"{record.id}.svg").write_text(render_card_image(record))

    # -- FeedbackRepository ---------------------------------------------

    async def get_lens_feedback_counts(
        self, organization_id: str | None
    ) -> dict[str, FeedbackSummary]:
        entries = self._read()
        counts: dict[str, FeedbackSummary] = {}
        for entry in entries:
            if organization_id is not None and entry.get("organization_id") not in (None, organization_id):
                continue
            lens = entry.get("lens")
            if not lens:
                continue
            summary = counts.setdefault(lens, FeedbackSummary())
            reaction = entry.get("reaction", "none")
            if reaction == "up":
                summary.up_count += 1
            elif reaction == "down":
                summary.down_count += 1
        return counts

    async def record_feedback(self, record: FeedbackRecord) -> None:
        found = await self.set_reaction(record.hypothesis_id, record.signal)
        if not found:
            raise KeyError(f"no stored hypothesis with id '{record.hypothesis_id}'")

    # -- HTTP-layer convenience (not part of either port) ----------------

    async def list_raw(self) -> list[dict[str, Any]]:
        return self._read()

    async def set_reaction(self, hypothesis_id: str, reaction: str) -> bool:
        if reaction not in REACTIONS:
            raise ValueError(f"reaction must be one of {REACTIONS}, got '{reaction}'")
        async with self._lock:
            entries = self._read()
            found = False
            for entry in entries:
                if entry.get("id") == hypothesis_id:
                    entry["reaction"] = reaction
                    found = True
                    break
            if found:
                self._write(entries)
            return found

    async def set_insight_reference(self, hypothesis_id: str, insight_package_id: str) -> bool:
        """Records that an insight_pipeline InsightPackage exists for this
        hypothesis, so the frontend can link "Read more" straight to the full
        report. Deliberately just an opaque string on the raw JSON entry (like
        `reaction`) rather than a HistoricalHypothesisRecord field — this
        package has no import of, or knowledge of, insight_pipeline's
        contracts; it only ever stores an id some external caller gave it."""
        async with self._lock:
            entries = self._read()
            found = False
            for entry in entries:
                if entry.get("id") == hypothesis_id:
                    entry["insightId"] = insight_package_id
                    found = True
                    break
            if found:
                self._write(entries)
            return found
