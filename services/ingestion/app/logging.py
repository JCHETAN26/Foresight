"""Structured logging setup (JSON in prod, console in local)."""

from __future__ import annotations

import logging

import structlog

from app.config import settings


def configure_logging() -> None:
    """Configure structlog + stdlib logging once at startup."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=level)

    renderer: structlog.types.Processor = (
        structlog.dev.ConsoleRenderer()
        if settings.env == "local"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
