import logging
import secrets

from anymail.exceptions import AnymailRequestsAPIError
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from employee.models import Employee

logger = logging.getLogger(__name__)

OTP_CACHE_PREFIX = "login_otp:"


def otp_cache_key(employee_pk) -> str:
    return f"{OTP_CACHE_PREFIX}{employee_pk}"


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def store_login_otp(employee: Employee, otp: str) -> None:
    cache.set(
        otp_cache_key(employee.pk),
        otp,
        timeout=settings.LOGIN_OTP_TIMEOUT,
    )


def verify_login_otp(employee: Employee, otp: str) -> bool:
    cached = cache.get(otp_cache_key(employee.pk))
    if cached is None or cached != otp:
        return False
    cache.delete(otp_cache_key(employee.pk))
    return True


def send_login_otp_email(employee: Employee, otp: str) -> bool:
    """Send the login OTP by email. Returns True if sent. In DEBUG, Resend/ESP
    failures are logged (including the OTP) and return False instead of raising.
    """
    timeout_minutes = settings.LOGIN_OTP_TIMEOUT // 60
    try:
        send_mail(
            subject="Your Security Guard App login code",
            message=(
                f"Hello {employee.get_full_name() or employee.employee_id},\n\n"
                f"Your login verification code is: {otp}\n\n"
                f"This code expires in {timeout_minutes} minutes. "
                "Do not share it with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[employee.email],
            fail_silently=False,
        )
    except AnymailRequestsAPIError as e:
        if settings.DEBUG:
            logger.warning(
                "Login OTP email failed (%s). Use a valid RESEND_API_KEY or unset "
                "it to use the console email backend. OTP for %s (pk=%s): %s",
                e,
                employee.email,
                employee.pk,
                otp,
            )
            return False
        raise
    return True
