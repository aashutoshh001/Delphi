"""Reuses hypothesis_agent's JSON logging setup rather than duplicating it —
one log format for the whole platform."""

from __future__ import annotations

import logging

from hypothesis_agent.logging_setup import JsonFormatter

_CONFIGURED = False


def configure_logging(level: str = "INFO", structured: bool = True) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter()
        if structured
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root = logging.getLogger("insight_pipeline")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"insight_pipeline.{name}")
