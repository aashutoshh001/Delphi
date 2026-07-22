from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    """Turns text into a vector for similarity/novelty checks. No dimension is
    contractually fixed — callers must not assume a specific length."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(y * y for y in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)
