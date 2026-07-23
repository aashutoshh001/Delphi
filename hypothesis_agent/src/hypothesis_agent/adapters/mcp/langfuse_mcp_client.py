"""Generic MCP client for Langfuse's own MCP server
(https://us.cloud.langfuse.com/api/public/mcp) — the same server registered
with Claude Code via `claude mcp add`, now reachable from the application
itself. Langfuse exposes ~80 tools this way: prompt management (getPrompt,
listPrompts, createTextPrompt, updatePromptLabels, ...), trace/observation
queries, datasets, evaluators, dashboards, scores, and more.

Read-only by construction: this Langfuse project is shared with other,
unrelated production systems (144+ prompts belonging to a different tool
were discovered here) — the same credentials that let hypothesis_agent read
those prompts for organizational context also technically allow
create/update/delete calls against that other system's live config.
call_tool() hard-rejects anything whose name doesn't start with "list",
"get", or "query" (Langfuse's own read-verb convention) before it ever
reaches the network, regardless of what the API key itself permits — so
"give the hypothesis agent context from these prompts" can never become
"the hypothesis agent modified someone else's prompt."

Deliberately NOT wired into AgentDependencies or the reasoning graph: the
search loop must keep working even if Langfuse is unreachable or
unconfigured. This is standalone infrastructure for scripts (see
examples/langfuse_mcp_demo.py) and any future node that explicitly opts in.

Credentials: reuses the same LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY /
LANGFUSE_HOST already used for LLM call tracing (see .env.example) — one
Langfuse configuration for the whole platform."""

from __future__ import annotations

import base64
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

_READ_ONLY_PREFIXES = ("list", "get", "query")


class LangfuseMCPClient:
    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
    ) -> None:
        try:
            import mcp  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "LangfuseMCPClient requires the 'mcp' package: install hypothesis_agent[observability]"
            ) from exc
        self._public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        self._secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        self._host = host or os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")
        if not self._public_key or not self._secret_key:
            raise ValueError(
                "LangfuseMCPClient requires LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "(env vars or constructor args)"
            )

    def _headers(self) -> dict[str, str]:
        token = base64.b64encode(f"{self._public_key}:{self._secret_key}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    @asynccontextmanager
    async def session(self) -> AsyncIterator[Any]:
        """One MCP session per call — Langfuse's endpoint is stateless HTTP,
        so there's no long-lived connection worth pooling here."""
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        url = f"{self._host.rstrip('/')}/api/public/mcp"
        async with streamablehttp_client(url, headers=self._headers()) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session

    async def list_tools(self) -> list[dict[str, Any]]:
        """Every tool the connected Langfuse project currently exposes —
        the full, current capability list, not a hardcoded subset. Includes
        write tools for visibility (`callable: False` marks the ones
        call_tool() will refuse) rather than hiding that they exist."""
        async with self.session() as session:
            result = await session.list_tools()
            return [
                {
                    "name": t.name,
                    "description": t.description or "",
                    "callable": t.name.startswith(_READ_ONLY_PREFIXES),
                }
                for t in result.tools
            ]

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Calls any *read-only* tool by name (see list_tools()) — e.g.
        call_tool("listPrompts") or call_tool("getPrompt", {"name": "critique"}).
        Returns the tool's text content joined; MCP tool results are
        loosely-typed by design (this server returns JSON-as-text).

        Raises PermissionError for anything that isn't a list/get/query call
        — see the module docstring for why. Not a suggestion, not
        configurable: this project is shared with systems this codebase has
        no business modifying."""
        if not name.startswith(_READ_ONLY_PREFIXES):
            raise PermissionError(
                f"LangfuseMCPClient is read-only — refusing to call '{name}'. "
                f"Only tools starting with {_READ_ONLY_PREFIXES} are permitted "
                "(this Langfuse project is shared with other systems)."
            )
        async with self.session() as session:
            result = await session.call_tool(name, arguments or {})
            texts = [c.text for c in result.content if getattr(c, "type", None) == "text"]
            return "\n".join(texts) if texts else str(result.content)
