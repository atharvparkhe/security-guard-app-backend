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


LOGIN_IDENTIFIER_FIELDS = (
    "employee_number",
    "employeeNumber",
    "employee_id",
    "employeeId",
    "username",
)


def coerce_login_request_data(data):
    """Map common web/client field names onto `employee_number`."""
    if not hasattr(data, "items"):
        return data
    payload = {key: data[key] for key in data}
    if payload.get("employee_number"):
        return payload
    for key in LOGIN_IDENTIFIER_FIELDS:
        if key == "employee_number":
            continue
        value = payload.get(key)
        if value not in (None, ""):
            payload["employee_number"] = value
            break
    return payload


def resolve_employee_for_login(identifier: str) -> Employee | None:
    """
    Resolve login by employee ID (EL + 3 digits) or by username.
    Web clients often send username in `employee_number`.
    """
    ident = (identifier or "").strip()
    if not ident:
        return None
    normalized = normalize_employee_number(ident)
    if EMPLOYEE_ID_RE.fullmatch(normalized):
        return get_employee_by_employee_number(normalized)
    return Employee.objects.filter(username__iexact=ident).first()


class LoginIdentifierSerializer(serializers.Serializer):
    employee_number = serializers.CharField(required=False, allow_blank=True)

    def to_internal_value(self, data):
        return super().to_internal_value(coerce_login_request_data(data))

    def resolve_login_employee(self, attrs):
        raw = (attrs.get("employee_number") or "").strip()
        if not raw:
            raise serializers.ValidationError(
                {"employee_number": ["This field is required."]}
            )
        employee = resolve_employee_for_login(raw)
        if employee is None:
            raise serializers.ValidationError(
                {"employee_number": ["User does not exist."]}
            )
        if not employee.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["employee"] = employee
        attrs["employee_number"] = employee.employee_id or raw
        return attrs


class LoginStep1Serializer(LoginIdentifierSerializer):
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        attrs = self.resolve_login_employee(attrs)
        if not attrs["employee"].check_password(attrs["password"]):
            raise serializers.ValidationError({"password": ["Invalid password."]})
        if not attrs["employee"].email:
            raise serializers.ValidationError(
                "No email is registered for this employee. Contact HR."
            )
        return attrs


class LoginStep2Serializer(LoginIdentifierSerializer):
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value

    def validate(self, attrs):
        return self.resolve_login_employee(attrs)


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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        if instance is None or not instance.pk:
            return attrs
        new_department = attrs.get("department", instance.department)
        for department in instance.headed_departments.all():
            if new_department is None or new_department.pk != department.pk:
                raise serializers.ValidationError(
                    {
                        "department": (
                            f'Cannot belong to a different department while serving '
                            f'as head of "{department.name}".'
                        )
                    }
                )
        return attrs


class ForgotPasswordSendOTPSerializer(LoginIdentifierSerializer):
    def validate(self, attrs):
        attrs = self.resolve_login_employee(attrs)
        if not attrs["employee"].email:
            raise serializers.ValidationError(
                "No email is registered for this employee. Contact HR."
            )
        return attrs


class ForgotPasswordVerifyOTPSerializer(LoginIdentifierSerializer):
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be a 6-digit number.")
        return value

    def validate(self, attrs):
        return self.resolve_login_employee(attrs)


class ForgotPasswordSetPasswordSerializer(LoginIdentifierSerializer):
    otp = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        return self.resolve_login_employee(attrs)


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
