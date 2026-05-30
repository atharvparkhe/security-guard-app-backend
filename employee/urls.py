from django.urls import path

from employee.views import (
    DepartmentListView,
    EmployeeDetailView,
    EmployeeListView,
    ForgotPasswordSendOTPView,
    ForgotPasswordSetPasswordView,
    ForgotPasswordVerifyOTPView,
    LoginStep1View,
    LoginStep2View,
    TokenRefreshView,
)

urlpatterns = [
    path("auth/login-step-1/", LoginStep1View.as_view(), name="auth-login-step-1"),
    path("auth/login-step-2/", LoginStep2View.as_view(), name="auth-login-step-2"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path(
        "auth/forgot-password/send-otp/",
        ForgotPasswordSendOTPView.as_view(),
        name="auth-forgot-password-send-otp",
    ),
    path(
        "auth/forgot-password/verify-otp/",
        ForgotPasswordVerifyOTPView.as_view(),
        name="auth-forgot-password-verify-otp",
    ),
    path(
        "auth/forgot-password/set-password/",
        ForgotPasswordSetPasswordView.as_view(),
        name="auth-forgot-password-set-password",
    ),
    path("employees/", EmployeeListView.as_view(), name="employee-list"),
    path("employees/<uuid:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
]
