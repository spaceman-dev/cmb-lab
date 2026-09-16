"""Job lifecycle contracts, shared by every asynchronous service."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}


class Job(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    service: str
    kind: str
    state: JobState = JobState.PENDING
    progress: float = 0.0
    message: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    celery_id: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobProgress(BaseModel):
    """Published to Redis pubsub and streamed to the browser over SSE."""

    job_id: UUID
    state: JobState
    progress: float = Field(ge=0.0, le=1.0)
    message: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
