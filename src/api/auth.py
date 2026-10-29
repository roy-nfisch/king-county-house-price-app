"""Optional bearer authentication for API requests."""

import secrets

from fastapi import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def authorized(request: Request) -> bool:
    """Check exactly one bearer credential when a token is configured."""
    configured = request.app.state.api_token
    if configured is None:
        return True
    headers = request.headers.getlist("authorization")
    parts = headers[0].split() if len(headers) == 1 else []
    return (
        len(parts) == 2
        and parts[0].lower() == "bearer"
        and parts[1].isascii()
        and secrets.compare_digest(parts[1], configured)
    )


class AuthenticationMiddleware:
    """Protect every HTTP route except the public readiness check."""

    def __init__(self, app: ASGIApp) -> None:
        """Store the application receiving authorized requests."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Reject unauthorized HTTP traffic before parsing a request body."""
        if scope["type"] == "http" and scope["path"] != "/health":
            if not authorized(Request(scope)):
                response = JSONResponse(
                    {"detail": "Unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
