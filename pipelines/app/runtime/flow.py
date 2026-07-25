"""Prefect-style @flow / @task decorators without an orchestrator server."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from app.runtime.logging import bound_log, setup_logging, teardown_logging

P = ParamSpec("P")
R = TypeVar("R")

_current_run: ContextVar[RunContext | None] = ContextVar("pipeline_run", default=None)


@dataclass
class TaskRun:
    name: str
    status: str  # pending | success | failed
    attempts: int = 0
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class RunContext:
    run_id: str
    flow_name: str
    started_at: datetime
    log_path: str | None = None
    tasks: list[TaskRun] = field(default_factory=list)


def get_run() -> RunContext | None:
    return _current_run.get()


def _new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def task(
    name: str | None = None,
    *,
    retries: int = 0,
    retry_delay: float = 1.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a function as a timed, optionally-retried pipeline task."""

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        task_name = name or getattr(fn, "__name__", "task")

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            run = get_run()
            flow_name = run.flow_name if run else "-"
            run_id = run.run_id if run else "-"
            record = TaskRun(name=task_name, status="pending")
            if run is not None:
                run.tasks.append(record)

            attempts_allowed = retries + 1
            last_exc: BaseException | None = None
            started = time.perf_counter()

            for attempt in range(1, attempts_allowed + 1):
                record.attempts = attempt
                task_log = bound_log(
                    run_id=run_id,
                    flow=flow_name,
                    task=task_name,
                    attempt=attempt,
                )
                task_log.debug("task starting")
                try:
                    result = fn(*args, **kwargs)
                    duration_ms = (time.perf_counter() - started) * 1000
                    record.status = "success"
                    record.duration_ms = duration_ms
                    bound_log(
                        run_id=run_id,
                        flow=flow_name,
                        task=task_name,
                        attempt=attempt,
                        duration_ms=round(duration_ms, 2),
                    ).info("task succeeded")
                    return result
                except BaseException as exc:
                    last_exc = exc
                    duration_ms = (time.perf_counter() - started) * 1000
                    bound_log(
                        run_id=run_id,
                        flow=flow_name,
                        task=task_name,
                        attempt=attempt,
                        error=str(exc),
                    ).warning("task attempt failed")
                    if attempt < attempts_allowed:
                        time.sleep(retry_delay)
                        continue
                    record.status = "failed"
                    record.duration_ms = duration_ms
                    record.error = str(exc)
                    bound_log(
                        run_id=run_id,
                        flow=flow_name,
                        task=task_name,
                        attempt=attempt,
                        duration_ms=round(duration_ms, 2),
                        error=str(exc),
                    ).error("task failed")
                    raise

            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def flow(name: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a function as a pipeline flow.

    Outermost call creates a ``RunContext``, configures logging, and emits a
    run summary. Nested calls join the active run as a subflow (same run_id,
    same log file).
    """

    def decorator(fn: Callable[P, R]) -> Callable[P, R]:
        flow_name = name or getattr(fn, "__name__", "flow")

        @wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            parent = get_run()
            if parent is not None:
                # Subflow: join the existing run.
                sub_log = bound_log(
                    run_id=parent.run_id,
                    flow=flow_name,
                    task="-",
                )
                sub_log.info("subflow starting")
                started = time.perf_counter()
                try:
                    result = fn(*args, **kwargs)
                    duration_ms = (time.perf_counter() - started) * 1000
                    bound_log(
                        run_id=parent.run_id,
                        flow=flow_name,
                        task="-",
                        duration_ms=round(duration_ms, 2),
                    ).success("subflow finished")
                    return result
                except BaseException as exc:
                    bound_log(
                        run_id=parent.run_id,
                        flow=flow_name,
                        task="-",
                        error=str(exc),
                    ).error("subflow failed")
                    raise

            run_id = _new_run_id()
            started_at = datetime.now(UTC)
            log_path = setup_logging(flow_name=flow_name, run_id=run_id)
            ctx = RunContext(
                run_id=run_id,
                flow_name=flow_name,
                started_at=started_at,
                log_path=str(log_path),
            )
            token = _current_run.set(ctx)
            params = _safe_params(args, kwargs)
            # Structured fields go through bind(); kwargs to info() are format-only.
            start_log = bound_log(
                run_id=run_id,
                flow=flow_name,
                task="-",
                log_path=str(log_path),
                **{f"param_{k}": v for k, v in params.items()},
            )
            start_log.info("flow starting")

            status = "success"
            try:
                return fn(*args, **kwargs)
            except BaseException as exc:
                status = "failed"
                bound_log(
                    run_id=run_id,
                    flow=flow_name,
                    task="-",
                    error=str(exc),
                ).exception("flow failed")
                raise
            finally:
                total_ms = (datetime.now(UTC) - started_at).total_seconds() * 1000
                _emit_summary(ctx, status=status, total_ms=total_ms)
                teardown_logging()
                _current_run.reset(token)

        return wrapper

    return decorator


def _safe_params(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, object]:
    params: dict[str, object] = {}
    for i, value in enumerate(args):
        params[f"arg{i}"] = _stringify(value)
    for key, value in kwargs.items():
        params[key] = _stringify(value)
    return params


def _stringify(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _emit_summary(ctx: RunContext, *, status: str, total_ms: float) -> None:
    succeeded = sum(1 for t in ctx.tasks if t.status == "success")
    failed = sum(1 for t in ctx.tasks if t.status == "failed")
    summary = bound_log(
        run_id=ctx.run_id,
        flow=ctx.flow_name,
        task="-",
        status=status,
        total_ms=round(total_ms, 2),
        tasks_total=len(ctx.tasks),
        tasks_succeeded=succeeded,
        tasks_failed=failed,
        log_path=ctx.log_path or "",
    )
    if status == "success":
        summary.success("flow finished")
    else:
        summary.error("flow finished with failure")

    for task_run in ctx.tasks:
        bound_log(
            run_id=ctx.run_id,
            flow=ctx.flow_name,
            task=task_run.name,
            status=task_run.status,
            attempts=task_run.attempts,
            duration_ms=round(task_run.duration_ms, 2),
            error=task_run.error or "",
        ).info("task summary")
