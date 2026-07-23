from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("INSIGHT_PIPELINE_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("INSIGHT_PIPELINE_SERVER_PORT", "8300"))
    uvicorn.run("insight_pipeline.server.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
