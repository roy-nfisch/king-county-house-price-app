"""Minimal prediction metadata logging, without request or result persistence."""

import json
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from starlette._utils import get_route_path
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class PredictionTrace:
    """Own one request's identity and timing; emit only operational metadata."""

    def __init__(self, model_version: str) -> None:
        """Start a trace for the loaded model; generate a server-owned UUID."""
        self.request_id = str(uuid4())
        self.model_version = model_version
        self.timestamp = datetime.now(UTC).isoformat()
        self._started = perf_counter()

    def finish(self, status_code: int | None, *, completed: bool = True) -> None:
        """Log outcome and timing; None means no response headers were observed.

        Completion is separate from HTTP status: a started 200 response can
        still be interrupted. Return None, without saving requests or results.
        """
        outcome = "success"
        if not completed or status_code is None or status_code >= 500:
            outcome = "failed"
        elif status_code >= 400:
            outcome = "rejected"
        logger.info(
            json.dumps(
                {
                    "request_id": self.request_id,
                    "timestamp": self.timestamp,
                    "model_version": self.model_version,
                    "outcome": outcome,
                    "status_code": status_code,
                    "duration_ms": round((perf_counter() - self._started) * 1000, 3),
                }
            )
        )


class PredictionTraceMiddleware:
    """Wrap prediction HTTP calls, including requests rejected before the route."""

    def __init__(self, app: ASGIApp) -> None:
        """Store the next ASGI application; do not load models or create traces."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Forward ASGI events, attach a request ID, and log one completion record.

        Non-prediction traffic passes through. Errors and cancellations propagate
        after a failed trace; a started HTTP status alone does not imply success.
        """
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or get_route_path(scope) != "/predict"
        ):
            await self.app(scope, receive, send)
            return
        trace = PredictionTrace(scope["app"].state.prediction_service.model_version)
        status_code = None
        completed = False

        async def traced_send(message: Message) -> None:
            """Attach server-generated correlation ID when response headers start."""
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                message.setdefault("headers", []).append(
                    (b"x-request-id", trace.request_id.encode("ascii"))
                )
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
            completed = True
        finally:
            trace.finish(status_code, completed=completed)
