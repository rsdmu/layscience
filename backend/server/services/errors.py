"""Custom exceptions representing user‑facing errors.

These exceptions carry structured information (error code, public message,
HTTP status and hint) that can be serialised into JSON responses.  They are
caught by the middleware in ``main.py`` and converted into error payloads.
"""

from typing import Optional


class UserFacingError(Exception):
    """Base class for errors that should be exposed to the client."""

    def __init__(
        self,
        code: str,
        public_message: str,
        where: str,
        status_code: int = 400,
        hint: Optional[str] = None,
    ) -> None:
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.status_code = status_code
        self.hint = hint
        self.where = where


class BadRequest(UserFacingError):
    """HTTP 400 for malformed requests."""

    def __init__(self, code: str, public_message: str, where: str, hint: Optional[str] = None) -> None:
        super().__init__(code=code, public_message=public_message, where=where, status_code=400, hint=hint)


class NotFound(UserFacingError):
    """HTTP 404 error."""

    def __init__(self, public_message: str, where: str, hint: Optional[str] = None) -> None:
        super().__init__(code="not_found", public_message=public_message, where=where, status_code=404, hint=hint)

