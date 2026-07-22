from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from hypothesis_agent.contracts.llm import LLMRequest, LLMResponse

T = TypeVar("T", bound=BaseModel)


class LLMService(ABC):
    """The one seam every reasoning-graph LLM call passes through. No node may
    call a model SDK directly — swapping providers means swapping the adapter
    bound to this port, nothing in reasoning/ changes."""

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def complete_structured(self, request: LLMRequest, schema: type[T]) -> T:
        """Returns a validated instance of `schema`. Implementations must
        raise rather than return a malformed object — callers never parse
        free text out of a completion themselves."""
        ...
