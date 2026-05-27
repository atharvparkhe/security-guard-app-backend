from rest_framework import serializers

from employee.models import Department, Employee
from employee.validators import EMPLOYEE_ID_RE


def normalize_employee_number(value: str) -> str:
    return (value or "").strip().upper()


def get_employee_by_employee_number(normalized: str) -> Employee | None:
    """Match `employee_id` case-insensitively; ignores blank/null employee_id."""
    if not normalized:
        return None
    return (
        Employee.objects.filter(employee_id__iexact=normalized)
        .exclude(employee_id__isnull=True)
        .exclude(employee_id="")
        .first()
    )


class LoginStep1Serializer(serializers.Serializer):
    employee_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_employee_number(self, value):
        normalized = normalize_employee_number(value)
        if not EMPLOYEE_ID_RE.fullmatch(normalized):
            raise serializers.ValidationError(
                'Employee number must be in the format "EL" followed by exactly '
                "three digits (e.g. EL000, EL001)."
            )
        return normalized

    def validate(self, attrs):
        employee = get_employee_by_employee_number(attrs["employee_number"])
        if employee is None:
            raise serializers.ValidationError(
                {"employee_number": ["User does not exist."]}
            )
        if not employee.is_active:
            raise serializers.ValidationError("User account is disabled.")
        if not employee.check_password(attrs["password"]):
            raise serializers.ValidationError({"password": ["Invalid password."]})
        if not employee.email:
            raise serializers.ValidationError(
                "No email is registered for this employee. Contact HR."
            )
        attrs["employee"] = employee
        return attrs


class LoginStep2Serializer(serializers.Serializer):
    employee_number = serializers.CharField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_employee_number(self, value):
        normalized = normalize_employee_number(value)
        if not EMPLOYEE_ID_RE.fullmatch(normalized):
            raise serializers.ValidationError(
                'Employee number must be in the format "EL" followed by exactly '
                "three digits (e.g. EL000, EL001)."
            )
        return normalized

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value

    def validate(self, attrs):
        employee = get_employee_by_employee_number(attrs["employee_number"])
        if employee is None:
            raise serializers.ValidationError(
                {"employee_number": ["User does not exist."]}
            )
        if not employee.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["employee"] = employee
        return attrs


class EmployeeSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    employee_number = serializers.CharField(source="employee_id", read_only=True)
    department = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "employee_number",
            "username",
            "full_name",
            "role",
            "department",
        )

    def get_department(self, obj):
        if obj.department_id:
            return {"name": obj.department.name}
        return None


class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Employee
        fields = (
            "id",
            "full_name",
            "role",
            "department_name",
            "phone",
        )


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)

    class Meta:
        model = Employee
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "employee_id",
            "role",
            "department",
            "department_name",
            "phone",
            "profile_photo",
            "is_active",
            "date_joined",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "username",
            "date_joined",
            "created_at",
            "updated_at",
        )


class EmployeePatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ("role", "department", "phone")


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = (
            "id",
            "name",
            "code",
            "description",
            "employee_count",
            "created_at",
        )
