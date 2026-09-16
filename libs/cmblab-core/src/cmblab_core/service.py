"""Shared FastAPI application factory.

Every Python service gets the same middleware, health endpoint, and error shape from here,
so that the gateway can treat them uniformly.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings

logger = logging.getLogger("cmblab")


def create_app(
    *,
    service_name: str,
    version: str = "0.1.0",
    description: str = "",
    on_startup: Callable[[], Any] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if on_startup:
            on_startup()
        logger.info("%s started", service_name)
        yield

    app = FastAPI(
        title=f"cmb-lab · {service_name}",
        version=version,
        description=description,
        lifespan=lifespan,
    )

    # The gateway is the public entry point, but allow direct browser access in dev.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8080"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id
        response.headers["x-service"] = service_name
        response.headers["x-elapsed-ms"] = f"{elapsed_ms:.1f}"
        return response

    @app.exception_handler(FileNotFoundError)
    async def handle_missing_data(_: Request, exc: FileNotFoundError):
        return JSONResponse(
            status_code=404,
            content={"error": "data_not_available", "detail": str(exc)},
        )

    @app.exception_handler(KeyError)
    async def handle_unknown_key(_: Request, exc: KeyError):
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "detail": str(exc).strip("'\"")},
        )

    @app.exception_handler(ValueError)
    async def handle_bad_value(_: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_request", "detail": str(exc)},
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, Any]:
        settings = get_settings()
        return {
            "status": "ok",
            "service": service_name,
            "version": version,
            "data_dir": str(settings.data_dir),
        }

    return app
