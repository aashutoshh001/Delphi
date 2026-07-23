"""One helper, reused everywhere an LLMRequest gets built: groups every LLM
call from a single hypothesis search (and, since insight_pipeline tags its
requests with the same id — see its own observability helper — the
subsequent investigation too) into one Langfuse session. A no-op dict when
no session_id is set, so nothing changes for callers/tests that don't have
one."""

from __future__ import annotations


def session_metadata(session_id: str | None) -> dict[str, str]:
    return {"session_id": session_id} if session_id else {}
