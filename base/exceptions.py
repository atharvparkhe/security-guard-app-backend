import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.views import exception_handler

from base.responses import error_response

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, ValidationError):
        detail = exc.detail
        if isinstance(detail, list):
            content = {"non_field_errors": detail}
        elif isinstance(detail, dict):
            content = {
                key: value if isinstance(value, list) else [value]
                for key, value in detail.items()
            }
        else:
            content = {"non_field_errors": [str(detail)]}
        return error_response(
            message="Validation failed",
            errors=content,
            status=response.status_code if response else status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, AuthenticationFailed):
        return error_response(
            message=str(exc.detail) if hasattr(exc, "detail") else "Authentication failed",
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        return error_response(
            message=str(exc) if str(exc) else "Permission denied",
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, (NotFound, Http404)):
        return error_response(
            message="Not found",
            status=status.HTTP_404_NOT_FOUND,
        )

    if response is not None:
        message = "An error occurred"
        content = {}
        if hasattr(exc, "detail"):
            if isinstance(exc.detail, str):
                message = exc.detail
            elif isinstance(exc.detail, dict):
                message = "An error occurred"
                content = exc.detail
            elif isinstance(exc.detail, list):
                message = exc.detail[0] if exc.detail else message
        return error_response(message=message, errors=content, status=response.status_code)

    if isinstance(exc, APIException):
        return error_response(
            message=str(exc.detail) if hasattr(exc, "detail") else str(exc),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    logger.exception("Unhandled exception", exc_info=exc)
    return error_response(
        message="Internal server error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
