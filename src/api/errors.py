"""Return serializable validation errors without echoing raw request values."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def invalid_request(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Return field locations/messages as 422, omitting input and error objects.

    Raw non-finite numbers cannot be encoded in a JSON response. Excluding input
    and context also avoids reflecting whole house records or Python exceptions.
    """
    details = [
        {key: item[key] for key in ("type", "loc", "msg")} for item in error.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": details})
