import logging
import secrets

from anymail.exceptions import AnymailRequestsAPIError
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from employee.models import Employee

logger = logging.getLogger(__name__)

OTP_CACHE_PREFIX = "forgot_password_otp:"
VERIFIED_CACHE_PREFIX = "forgot_password_verified:"


def otp_cache_key(employee_pk) -> str:
    return f"{OTP_CACHE_PREFIX}{employee_pk}"


def verified_cache_key(employee_pk) -> str:
    return f"{VERIFIED_CACHE_PREFIX}{employee_pk}"


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def store_forgot_password_otp(employee: Employee, otp: str) -> None:
    cache.set(
        otp_cache_key(employee.pk),
        otp,
        timeout=settings.LOGIN_OTP_TIMEOUT,
    )


def verify_forgot_password_otp(employee: Employee, otp: str) -> bool:
    cached = cache.get(otp_cache_key(employee.pk))
    if cached is None or cached != otp:
        return False
    cache.delete(otp_cache_key(employee.pk))
    cache.set(
        verified_cache_key(employee.pk),
        "1",
        timeout=settings.LOGIN_OTP_TIMEOUT,
    )
    return True


def consume_forgot_password_verified(employee: Employee, otp: str) -> bool:
    """Allow set-password when OTP was verified in step 2 (cached) or matches fresh OTP."""
    if cache.get(verified_cache_key(employee.pk)):
        cache.delete(verified_cache_key(employee.pk))
        return True
    cached = cache.get(otp_cache_key(employee.pk))
    if cached and cached == otp:
        cache.delete(otp_cache_key(employee.pk))
        return True
    return False


def send_forgot_password_otp_email(employee: Employee, otp: str) -> bool:
    timeout_minutes = settings.LOGIN_OTP_TIMEOUT // 60
    try:
        send_mail(
            subject="Your Security Guard App password reset code",
            message=(
                f"Hello {employee.get_full_name() or employee.employee_id},\n\n"
                f"Your password reset code is: {otp}\n\n"
                f"This code expires in {timeout_minutes} minutes."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.email],
            fail_silently=False,
        )
    except AnymailRequestsAPIError as e:
        if settings.DEBUG:
            logger.warning(
                "Forgot-password OTP email failed (%s). OTP for %s: %s",
                e,
                employee.email,
                otp,
            )
            return False
        raise
    return True
