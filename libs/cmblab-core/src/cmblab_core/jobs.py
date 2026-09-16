"""In-process background job manager.

MCMC sampling and Monte Carlo simulation take minutes, which is far too long for an HTTP
request but short enough that a full Celery deployment is overkill during development. This
runs jobs on a thread pool and exposes progress for polling.

The heavy work inside these jobs is numpy and CAMB, which release the GIL, so threads give
real parallelism here. Swapping in Celery later means replacing :meth:`JobManager.submit`
and nothing else.
"""

from __future__ import annotations

import threading
import traceback
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

JobFunction = Callable[..., Any]
ProgressFn = Callable[[float, str], None]


@dataclass
class JobRecord:
    id: str
    kind: str
    state: str = "pending"  # pending | running | succeeded | failed | cancelled
    progress: float = 0.0
    message: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @property
    def elapsed_s(self) -> float:
        if not self.started_at:
            return 0.0
        end = self.finished_at or datetime.now(UTC)
        return (end - self.started_at).total_seconds()

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "state": self.state,
            "progress": round(self.progress, 4),
            "message": self.message,
            "params": self.params,
            "error": self.error,
            "elapsed_s": round(self.elapsed_s, 2),
            "created_at": self.created_at.isoformat(),
        }


class JobManager:
    """Thread-pool job runner with progress reporting and a bounded history."""

    def __init__(self, max_workers: int = 2, history: int = 100) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="cmblab-job")
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()
        self._history = history

    def submit(self, kind: str, fn: JobFunction, params: dict[str, Any] | None = None) -> str:
        """Queue ``fn`` for execution. ``fn`` receives a ``progress`` keyword callable."""
        job_id = uuid.uuid4().hex[:16]
        record = JobRecord(id=job_id, kind=kind, params=params or {})

        with self._lock:
            self._jobs[job_id] = record
            self._order.append(job_id)
            while len(self._order) > self._history:
                self._jobs.pop(self._order.pop(0), None)

        def report(fraction: float, message: str = "") -> None:
            record.progress = max(0.0, min(1.0, fraction))
            if message:
                record.message = message

        def run() -> None:
            record.state = "running"
            record.started_at = datetime.now(UTC)
            try:
                record.result = fn(progress=report)
                record.state = "succeeded"
                record.progress = 1.0
                record.message = record.message or "complete"
            except Exception as exc:  # noqa: BLE001 - surfaced through the job record
                record.state = "failed"
                record.error = f"{type(exc).__name__}: {exc}"
                record.message = "failed"
                traceback.print_exc()
            finally:
                record.finished_at = datetime.now(UTC)

        self._pool.submit(run)
        return job_id

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"No job with id {job_id}")
            return self._jobs[job_id]

    def list(self, kind: str | None = None, limit: int = 25) -> list[JobRecord]:
        with self._lock:
            records = [self._jobs[i] for i in reversed(self._order) if i in self._jobs]
        if kind:
            records = [r for r in records if r.kind == kind]
        return records[:limit]
