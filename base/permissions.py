from rest_framework.permissions import BasePermission

from employee.models import Employee


class RolePermission(BasePermission):
    """Role-gated access; superadmin bypasses all role checks."""

    allowed_roles = ()

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == Employee.ROLE_SUPERADMIN:
            return True
        return request.user.role in self.allowed_roles


class IsSecurityGuard(RolePermission):
    allowed_roles = ("security_guard",)


class IsStoresManager(RolePermission):
    allowed_roles = ("stores_manager",)


class IsGuardOrStoresManager(RolePermission):
    allowed_roles = ("security_guard", "stores_manager")


class IsInwardListReader(RolePermission):
    allowed_roles = ("security_guard", "stores_manager", "superadmin")


class IsPurchase(RolePermission):
    allowed_roles = ("purchase",)


class IsHR(RolePermission):
    allowed_roles = ("hr",)


class IsSuperAdmin(RolePermission):
    allowed_roles = ("superadmin",)
