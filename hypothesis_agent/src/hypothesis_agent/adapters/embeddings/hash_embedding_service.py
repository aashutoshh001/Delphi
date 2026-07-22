from __future__ import annotations

import hashlib
import re

from hypothesis_agent.ports.embedding_service import EmbeddingService

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class HashEmbeddingService(EmbeddingService):
    """Deterministic, dependency-free embedding via feature hashing. Not
    semantically strong, but requires no API key/network — the default so the
    system is runnable offline out of the box. Swap for a real embedding
    model via config with no change elsewhere."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = sum(v * v for v in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]
