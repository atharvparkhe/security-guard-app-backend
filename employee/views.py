from django.db import models
from django.db.models import Count
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from base.permissions import IsSuperAdmin
from base.views import BaseAPIView
from employee.models import Department, Employee
from employee.login_otp import generate_otp, send_login_otp_email, store_login_otp, verify_login_otp
from employee.serializers import (
    DepartmentSerializer,
    EmployeeDetailSerializer,
    EmployeeListSerializer,
    EmployeePatchSerializer,
    EmployeeSummarySerializer,
    LoginStep1Serializer,
    LoginStep2Serializer,
)


class LoginStep1View(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginStep1Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.validated_data["employee"]
        otp = generate_otp()
        store_login_otp(employee, otp)
        emailed = send_login_otp_email(employee, otp)
        if emailed:
            return self.success(
                message="OTP sent to your registered email address.",
            )
        return self.success(
            message=(
                "Email could not be sent (development). The OTP was written to the "
                "Django server log; fix RESEND_API_KEY or remove it to use console email."
            ),
        )


class LoginStep2View(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginStep2Serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = serializer.validated_data["employee"]
        if not verify_login_otp(employee, serializer.validated_data["otp"]):
            return self.error(message="Invalid OTP.")
        refresh = RefreshToken.for_user(employee)
        return self.success(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "employee": EmployeeSummarySerializer(employee).data,
            },
            message="Login successful",
        )


class TokenRefreshView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenRefreshSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            # When the refresh token is expired/invalid/blacklisted, SimpleJWT raises TokenError.
            # Convert it into an explicit 401 instead of letting it bubble up as a 500.
            return self.error(
                message=(
                    "Unauthorized: refresh token is invalid or has been revoked. "
                    "Please log in again."
                ),
                status=401,
            )
        except ValidationError as exc:
            # Missing/incorrect payload (e.g. no refresh token) should also be treated as unauthorized
            # for this endpoint to keep client behavior consistent.
            return self.error(
                message="Unauthorized: refresh token is missing or invalid.",
                errors=getattr(exc, "detail", None),
                status=401,
            )

        return self.success(
            data=serializer.validated_data,
            message="Token refreshed successfully",
        )


class EmployeeListView(BaseAPIView):
    def get(self, request):
        qs = Employee.objects.filter(is_active=True)
        role = request.query_params.get("role")
        department = request.query_params.get("department")
        if role:
            qs = qs.filter(role=role)
        if department:
            qs = qs.filter(department_id=department)
        data = EmployeeListSerializer(qs, many=True).data
        return self.success(data=data, message="Employees retrieved successfully")


class EmployeeDetailView(BaseAPIView):
    def get(self, request, pk):
        try:
            employee = Employee.objects.get(pk=pk, is_active=True)
        except Employee.DoesNotExist:
            return self.error(message="Employee not found", status=404)
        return self.success(
            data=EmployeeDetailSerializer(employee).data,
            message="Employee retrieved successfully",
        )

    def patch(self, request, pk):
        if request.user.role != Employee.ROLE_SUPERADMIN:
            return self.error(message="Permission denied", status=403)
        try:
            employee = Employee.objects.get(pk=pk)
        except Employee.DoesNotExist:
            return self.error(message="Employee not found", status=404)
        serializer = EmployeePatchSerializer(
            employee,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(
            data=EmployeeDetailSerializer(employee).data,
            message="Employee updated successfully",
        )


class DepartmentListView(BaseAPIView):
    def get(self, request):
        qs = Department.objects.annotate(
            employee_count=Count(
                "employees",
                filter=models.Q(employees__is_active=True),
            )
        )
        data = DepartmentSerializer(qs, many=True).data
        return self.success(data=data, message="Departments retrieved successfully")
