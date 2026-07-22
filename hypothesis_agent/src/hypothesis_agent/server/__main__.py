from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("HYPOTHESIS_AGENT_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("HYPOTHESIS_AGENT_SERVER_PORT", "8200"))
    uvicorn.run("hypothesis_agent.server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
