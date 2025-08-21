from typing import Optional

class UserFacingError(Exception):
    def __init__(self, code: str, public_message: str, where: str, status_code: int = 400, hint: Optional[str] = None):
        super().__init__(public_message)
        self.code = code
        self.public_message = public_message
        self.status_code = status_code
        self.hint = hint
        self.where = where

class BadRequest(UserFacingError):
    def __init__(self, code: str, public_message: str, where: str, hint: Optional[str] = None):
        super().__init__(code=code, public_message=public_message, where=where, status_code=400, hint=hint)

class NotFound(UserFacingError):
    def __init__(self, public_message: str, where: str, hint: Optional[str] = None):
        super().__init__(code="not_found", public_message=public_message, where=where, status_code=404, hint=hint)