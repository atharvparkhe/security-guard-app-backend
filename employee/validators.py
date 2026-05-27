import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Human-readable employee ID: "EL" + exactly 3 digits (e.g. EL000, EL042).
EMPLOYEE_ID_RE = re.compile(r"^EL\d{3}$")


def validate_employee_id_field(value):
    """
    Field-level validator for ``Employee.employee_id``.
    Empty values are allowed (null/blank on the field).
    """
    if value in (None, ""):
        return
    normalized = str(value).strip().upper()
    if normalized == "":
        return
    if not EMPLOYEE_ID_RE.fullmatch(normalized):
        raise ValidationError(
            _(
                'Employee ID must be in the format "EL" followed by exactly three '
                "digits (e.g. EL000, EL042)."
            ),
            code="invalid_employee_id_format",
        )
