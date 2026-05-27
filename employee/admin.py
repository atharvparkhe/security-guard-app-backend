from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from employee.admin_forms import (
    SimpleAdminPasswordChangeForm,
    SimpleAdminUserCreationForm,
)
from employee.models import Department, Employee


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "head", "is_active")
    search_fields = ("name", "code")
    list_filter = ("is_active",)


@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    add_form = SimpleAdminUserCreationForm
    change_password_form = SimpleAdminPasswordChangeForm

    list_display = (
        "username",
        "full_name",
        "role",
        "department",
        "is_active",
        "date_joined",
    )
    list_filter = ("role", "department", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    fieldsets = UserAdmin.fieldsets + (
        (
            "Employee details",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "role",
                    "phone",
                    "profile_photo",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Employee details",
            {
                "fields": (
                    "employee_id",
                    "department",
                    "role",
                    "phone",
                )
            },
        ),
    )

    @admin.display(description="Full name")
    def full_name(self, obj):
        return obj.get_full_name()
