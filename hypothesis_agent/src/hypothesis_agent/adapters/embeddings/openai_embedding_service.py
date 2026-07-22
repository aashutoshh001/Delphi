from __future__ import annotations

from hypothesis_agent.ports.embedding_service import EmbeddingService


class OpenAIEmbeddingService(EmbeddingService):
    """Real embedding backend. `openai` is an optional extra
    (`hypothesis_agent[llm-openai]`) — importing it lazily keeps it out of the
    core dependency graph."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None) -> None:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise ImportError(
                "OpenAIEmbeddingService requires the 'openai' package: "
                "install hypothesis_agent[llm-openai]"
            ) from exc
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=text)
        return list(response.data[0].embedding)
