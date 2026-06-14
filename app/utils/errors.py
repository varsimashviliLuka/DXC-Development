"""Custom exceptions."""

class AppError(Exception):
  status_code = 400

  def __init__(self, message, status_code=None):
    super().__init__(message)
    self.message = message
    if status_code is not None:
      self.status_code = status_code


class NotFoundError(AppError):
  status_code = 404


class ForbiddenError(AppError):
  status_code = 403


class UnauthorizedError(AppError):
  status_code = 401


class ConflictError(AppError):
  status_code = 409
