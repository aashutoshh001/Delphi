"""Proves LangfuseMCPClient actually reaches your Langfuse project and can
call real tools — lists everything the MCP server exposes, then makes a
couple of real calls (prompts, health, recent observations) so you can see
real data come back, not just a successful handshake.

Requires LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY (see hypothesis_agent/.env)
and the `observability` extra: pip install -e ".[observability]"

    python examples/langfuse_mcp_demo.py
"""

from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv

from hypothesis_agent.adapters.mcp.langfuse_mcp_client import LangfuseMCPClient

load_dotenv(".env")


async def main() -> None:
    client = LangfuseMCPClient()

    tools = await client.list_tools()
    print(f"=== {len(tools)} tools available on this Langfuse MCP server ===")
    for t in tools:
        print(f"- {t['name']}: {t['description'][:90]}")

    print("\n=== getHealth() ===")
    print(await client.call_tool("getHealth"))

    print("\n=== listPrompts() — your project's managed prompts ===")
    print(await client.call_tool("listPrompts", {"limit": 20}))

    print("\n=== listObservations() — 5 most recent LLM calls ===")
    result = await client.call_tool("listObservations", {"limit": 5, "type": "GENERATION"})
    try:
        parsed = json.loads(result)
        print(json.dumps(parsed, indent=2)[:2000])
    except json.JSONDecodeError:
        print(result[:2000])


if __name__ == "__main__":
    asyncio.run(main())
