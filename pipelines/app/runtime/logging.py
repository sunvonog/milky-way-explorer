"""Structured logging via logly 0.2.1 (Loguru-shaped API).

One Logger instance for the process. Console sink for humans; a per-run
JSON-lines file under ``settings.logs_root / <flow> / <run_id>.jsonl`` for
machine inspection. Structured fields go through ``bind()`` / ``contextualize()``
— kwargs to ``info()`` etc. are format-string substitutions only.
"""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from logly import Logger

from app.config import get_settings

log = Logger(name="pipelines")

_console_handler: int | None = None
_file_handler: int | None = None
_configured = False


def _console_format() -> str:
    return "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {extra[flow]}:{extra[task]} | {message}"


def setup_logging(*, flow_name: str, run_id: str) -> Path:
    """Configure console + per-run JSON sinks. Returns the run log path."""
    global _console_handler, _file_handler, _configured

    settings = get_settings()
    # Drop previous sinks so a second top-level flow in the same process
    # does not duplicate console/file handlers.
    log.remove()

    level = settings.log_level.upper()
    colorize = settings.log_color and not settings.log_json

    if settings.log_json:
        _console_handler = log.add(
            sys.stderr,
            level=level,
            serialize=True,
            colorize=False,
            enqueue=False,
        )
    else:
        _console_handler = log.add(
            sys.stderr,
            level=level,
            colorize=colorize,
            format=_console_format(),
            enqueue=False,
        )

    run_dir = settings.logs_root / flow_name
    run_dir.mkdir(parents=True, exist_ok=True)
    run_log_path = run_dir / f"{run_id}.jsonl"
    _file_handler = log.add(
        str(run_log_path),
        level="DEBUG",
        serialize=True,
        enqueue=True,
    )

    _prune_old_runs(run_dir, settings.log_retention)
    _configured = True
    return run_log_path


def teardown_logging() -> None:
    """Flush async writes. Safe to call even if setup never ran."""
    log.complete()


def _prune_old_runs(run_dir: Path, keep: int) -> None:
    if keep <= 0:
        return
    files = sorted(run_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[keep:]:
        with contextlib.suppress(OSError):
            stale.unlink()


def bound_log(**fields: object) -> Logger:
    """Return a logger with structured fields bound into every record."""
    return log.bind(**fields)
