from django.db.models import Q

from employee.models import Employee
from gate.models import InwardEntry


def build_inward_list_queryset(base_qs, user, start_date, end_date):
    """Role-scoped inward list queryset for the date range on created_at."""
    qs = base_qs.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    if user.role == Employee.ROLE_SECURITY_GUARD:
        qs = qs.filter(gate_transaction__guard=user)
    return qs.order_by("-created_at")


def apply_inward_status_filter(qs, status):
    if status:
        return qs.filter(status=status)
    return qs


def build_inward_list_stats(qs, user):
    if user.role == Employee.ROLE_SUPERADMIN:
        return build_inward_list_stats_superadmin(qs)
    return {
        "total_completed": qs.filter(status=InwardEntry.STATUS_COMPLETED).count(),
        "vehicles_inside": qs.filter(
            gate_transaction__in_time__isnull=False,
            gate_transaction__out_time__isnull=True,
        ).count(),
    }


def build_inward_list_stats_superadmin(qs):
    no_hardcopy_q = Q(stores_acknowledgment__isnull=True) | Q(
        stores_acknowledgment__hardcopy_received=False
    )
    pending_grn_q = Q(stores_acknowledgment__isnull=True) | Q(
        stores_acknowledgment__grn_number=""
    )
    return {
        "completed": qs.filter(status=InwardEntry.STATUS_COMPLETED).count(),
        "pending": qs.filter(
            status=InwardEntry.STATUS_PENDING_VERIFICATION
        ).count(),
        "pending_grn": qs.filter(pending_grn_q).count(),
        "no_invoice_hardcopy": qs.filter(no_hardcopy_q).count(),
    }


def serialize_inward_list_results(entries, request, user):
    from gate.utils import (
        serialize_inward_list_item,
        serialize_inward_list_item_superadmin,
    )

    if user.role == Employee.ROLE_SUPERADMIN:
        return [
            serialize_inward_list_item_superadmin(entry, request)
            for entry in entries
        ]
    return [serialize_inward_list_item(entry, request) for entry in entries]
