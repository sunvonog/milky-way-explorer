"""Single entry point for offline pipelines.

Usage::

    uv run python -m app.main                      # full canonical build
    uv run python -m app.main --strict             # fail on expectation misses
    uv run python -m app.main --log-level DEBUG
    uv run python -m app.main refresh-snapshots    # maintainer-only path
"""

from __future__ import annotations

import argparse
import sys

from app.config import override_settings
from app.flows.exoplanets import refresh_pscomppars
from app.flows.identity import build_identity
from app.flows.snapshots import refresh_snapshots
from app.runtime.flow import flow


@flow(name="canonical-build")
def canonical_build() -> None:
    """Parent flow: identity resolution, then future Gaia / density / publish steps."""
    build_identity()
    # future: gaia enrichment, density aggregation, publication


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m app.main",
        description="Milky Way Explorer offline pipelines",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="build",
        choices=["build", "refresh-snapshots", "refresh-pscomppars"],
        help="pipeline to run (default: build)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="fail the run when expectation checks miss",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"],
        help="override MWE_LOG_LEVEL",
    )
    parser.add_argument(
        "--log-json",
        action="store_true",
        default=None,
        help="emit JSON on the console (useful in CI)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    overrides: dict[str, object] = {}
    if args.strict:
        overrides["strict_checks"] = True
    if args.log_level is not None:
        overrides["log_level"] = args.log_level
    if args.log_json:
        overrides["log_json"] = True
    if overrides:
        override_settings(**overrides)

    try:
        if args.command == "refresh-snapshots":
            refresh_snapshots()
        elif args.command == "refresh-pscomppars":
            refresh_pscomppars()
        else:
            canonical_build()
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (1 if code else 0)
    except Exception:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
