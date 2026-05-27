from django.urls import path

from employee.views import (
    DepartmentListView,
    EmployeeDetailView,
    EmployeeListView,
    LoginStep1View,
    LoginStep2View,
    TokenRefreshView,
)

urlpatterns = [
    path("auth/login-step-1/", LoginStep1View.as_view(), name="auth-login-step-1"),
    path("auth/login-step-2/", LoginStep2View.as_view(), name="auth-login-step-2"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"),
    path("employees/", EmployeeListView.as_view(), name="employee-list"),
    path("employees/<uuid:pk>/", EmployeeDetailView.as_view(), name="employee-detail"),
    path("departments/", DepartmentListView.as_view(), name="department-list"),
]
