import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel
from employee.validators import validate_employee_id_field


def validate_department_head_belongs_to_department(head, department):
    """Department head must be a member of that department."""
    if head is None:
        return
    if head.department_id is None:
        raise ValidationError(
            _("Department head must be assigned to a department."),
            code="head_missing_department",
        )
    if department.pk and head.department_id != department.pk:
        raise ValidationError(
            _("Department head must belong to this department."),
            code="head_wrong_department",
        )


class Department(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    head = models.ForeignKey(
        "Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def clean(self):
        super().clean()
        if self.head_id:
            validate_department_head_belongs_to_department(self.head, self)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.head_id:
            validate_department_head_belongs_to_department(self.head, self)

    def __str__(self):
        return self.name


class Employee(AbstractUser):
    ROLE_SECURITY_GUARD = "security_guard"
    ROLE_STORES_MANAGER = "stores_manager"
    ROLE_PURCHASE = "purchase"
    ROLE_HR = "hr"
    ROLE_SUPERADMIN = "superadmin"

    ROLE_CHOICES = [
        (ROLE_SECURITY_GUARD, "Security Guard"),
        (ROLE_STORES_MANAGER, "Stores Manager"),
        (ROLE_PURCHASE, "Purchase"),
        (ROLE_HR, "HR"),
        (ROLE_SUPERADMIN, "Super Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[validate_employee_id_field],
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employees",
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_SECURITY_GUARD,
    )
    phone = models.CharField(max_length=15, blank=True)
    profile_photo = models.ImageField(
        upload_to="employee_photos/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["first_name", "last_name"]

    def clean(self):
        super().clean()
        raw = self.employee_id
        if raw is not None:
            s = str(raw).strip()
            if s == "":
                self.employee_id = None
            else:
                self.employee_id = s.upper()

        self._validate_headed_departments()

    def _validate_headed_departments(self):
        if not self.pk:
            return
        for department in self.headed_departments.all():
            validate_department_head_belongs_to_department(self, department)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._validate_headed_departments()

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    @property
    def full_name(self):
        return self.get_full_name() or self.username
