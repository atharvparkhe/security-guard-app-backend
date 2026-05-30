from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from django.db.models.functions import ExtractHour, TruncDate

from core.settings import configurations
from gate.models import Driver, InwardEntry, Invoice, OutwardEntry, Truck, VisitorEntry
from orders.models import PurchaseOrder

RECENT_LIMIT = 10

VISIBILITY = {
    "gate": True,
    "invoices": True,
    "purchase_orders": True,
    "stores": True,
    "master_data": True,
}


def _inward_period_qs(start_date, end_date):
    return InwardEntry.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).select_related("truck", "driver", "invoice", "gate_transaction")


def _invoice_period_qs(start_date, end_date):
    return Invoice.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )


def _po_period_qs(start_date, end_date):
    return PurchaseOrder.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).select_related("vendor")


def _build_kpis(inward_qs, invoice_qs, po_qs, start_date, end_date):
    inward_agg = inward_qs.aggregate(
        inward_total=Count("id"),
        inward_completed=Count("id", filter=Q(status=InwardEntry.STATUS_COMPLETED)),
        vehicles_inside_in_period=Count(
            "id",
            filter=Q(
                gate_transaction__in_time__isnull=False,
                gate_transaction__out_time__isnull=True,
            ),
        ),
        pending_verification=Count(
            "id",
            filter=Q(status=InwardEntry.STATUS_PENDING_VERIFICATION),
        ),
        grn_generated=Count(
            "id",
            filter=Q(status=InwardEntry.STATUS_GRN_GENERATED),
        ),
        rejected=Count(
            "id",
            filter=Q(status=InwardEntry.STATUS_REJECTED),
        ),
    )

    currently_inside = InwardEntry.objects.filter(
        gate_transaction__in_time__isnull=False,
        gate_transaction__out_time__isnull=True,
    ).count()

    return {
        "inward_total": inward_agg["inward_total"] or 0,
        "inward_completed": inward_agg["inward_completed"] or 0,
        "vehicles_inside_in_period": inward_agg["vehicles_inside_in_period"] or 0,
        "currently_inside": currently_inside,
        "pending_verification": inward_agg["pending_verification"] or 0,
        "grn_generated": inward_agg["grn_generated"] or 0,
        "rejected": inward_agg["rejected"] or 0,
        "outward_today": OutwardEntry.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).count(),
        "pending_returns": OutwardEntry.objects.filter(
            status=OutwardEntry.STATUS_PENDING_RETURN
        ).count(),
        "overdue_returns": OutwardEntry.objects.filter(
            status=OutwardEntry.STATUS_PENDING_RETURN,
            expected_return_date__lt=timezone.localdate(),
        ).count(),
        "visitors_today": VisitorEntry.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).count(),
        "visitors_inside": VisitorEntry.objects.filter(
            status=VisitorEntry.STATUS_INSIDE
        ).count(),
        "invoices_count": invoice_qs.count(),
        "purchase_orders_count": po_qs.count(),
        "drivers_total": Driver.objects.filter(is_active=True).count(),
        "trucks_total": Truck.objects.filter(is_active=True).count(),
    }


def _build_inward_by_status(inward_qs):
    counts = {
        row["status"]: row["count"]
        for row in inward_qs.values("status").annotate(count=Count("id"))
    }
    return [
        {
            "status": status,
            "label": label,
            "count": counts.get(status, 0),
        }
        for status, label in InwardEntry.STATUS_CHOICES
    ]


def _build_inward_by_hour(inward_qs, start_date, end_date):
    if start_date != end_date:
        return []

    hour_counts = {
        row["hour"]: row["count"]
        for row in inward_qs.filter(gate_transaction__in_time__isnull=False)
        .annotate(hour=ExtractHour("gate_transaction__in_time"))
        .values("hour")
        .annotate(count=Count("id"))
    }
    return [
        {
            "hour": hour,
            "label": f"{hour:02d}:00",
            "count": hour_counts.get(hour, 0),
        }
        for hour in range(24)
    ]


def _build_daily_comparison(inward_qs, invoice_qs, start_date, end_date):
    if (end_date - start_date).days > 6:
        return []

    completed_by_day = {
        row["day"]: row["count"]
        for row in inward_qs.filter(status=InwardEntry.STATUS_COMPLETED)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    }
    invoices_by_day = {
        row["day"]: row["count"]
        for row in invoice_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    }

    results = []
    current = start_date
    while current <= end_date:
        results.append(
            {
                "date": current.isoformat(),
                "inwards_completed": completed_by_day.get(current, 0),
                "invoices": invoices_by_day.get(current, 0),
            }
        )
        current += timedelta(days=1)
    return results


def _serialize_recent_inward(entry):
    gt = entry.gate_transaction
    return {
        "id": str(entry.id),
        "status": entry.status,
        "registration_number": entry.truck.registration_number,
        "driver_name": entry.driver.name,
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "out_time": gt.out_time.isoformat() if gt.out_time else None,
        "invoice_number": entry.invoice.invoice_number,
    }


def _serialize_recent_invoice(invoice):
    entry = invoice.inward_entries.order_by("-created_at").first()
    inward_entry_id = str(entry.id) if entry else None
    return {
        "id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "vendor_name": invoice.supplier_name,
        "invoice_amount": (
            str(invoice.invoice_amount) if invoice.invoice_amount is not None else None
        ),
        "invoice_date": (
            invoice.invoice_date.isoformat() if invoice.invoice_date else None
        ),
        "inward_entry_id": inward_entry_id,
        "status": "linked" if inward_entry_id else "unlinked",
    }


def _serialize_recent_po(po):
    return {
        "id": str(po.id),
        "po_number": po.po_number,
        "vendor_name": po.vendor.name,
        "status": po.status,
        "created_at": po.created_at.isoformat(),
    }


def _serialize_currently_inside(entry):
    gt = entry.gate_transaction
    return {
        "id": str(entry.id),
        "registration_number": entry.truck.registration_number,
        "driver_name": entry.driver.name,
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "status": entry.status,
    }


def _build_recent(inward_qs, invoice_qs, po_qs):
    recent_inwards = [
        _serialize_recent_inward(entry)
        for entry in inward_qs.order_by("-gate_transaction__in_time")[:RECENT_LIMIT]
    ]

    recent_invoices = [
        _serialize_recent_invoice(inv)
        for inv in invoice_qs.prefetch_related("inward_entries").order_by("-created_at")[
            :RECENT_LIMIT
        ]
    ]

    recent_pos = [
        _serialize_recent_po(po)
        for po in po_qs.order_by("-created_at")[:RECENT_LIMIT]
    ]

    live_qs = (
        InwardEntry.objects.filter(
            gate_transaction__in_time__isnull=False,
            gate_transaction__out_time__isnull=True,
        )
        .select_related("truck", "driver", "gate_transaction")
        .order_by("gate_transaction__in_time")[:RECENT_LIMIT]
    )
    currently_inside = [_serialize_currently_inside(entry) for entry in live_qs]

    return {
        "inwards": recent_inwards,
        "invoices": recent_invoices,
        "purchase_orders": recent_pos,
        "currently_inside": currently_inside,
    }


def _build_alerts(kpis):
    alerts = []
    if kpis.get("overdue_returns", 0) >= 1:
        count = kpis["overdue_returns"]
        alerts.append(
            {
                "severity": "warning",
                "code": "OVERDUE_RETURNABLES",
                "message": f"{count} returnable outward entr{'y' if count == 1 else 'ies'} overdue",
            }
        )
    if kpis["pending_verification"] >= 1:
        count = kpis["pending_verification"]
        alerts.append(
            {
                "severity": "warning",
                "code": "PENDING_VERIFICATION_HIGH",
                "message": (
                    f"{count} entr{'y' if count == 1 else 'ies'} awaiting stores verification"
                ),
            }
        )
    threshold = configurations.DASHBOARD_VEHICLES_INSIDE_ALERT_THRESHOLD
    if kpis["currently_inside"] >= threshold:
        count = kpis["currently_inside"]
        alerts.append(
            {
                "severity": "info",
                "code": "VEHICLES_INSIDE_HIGH",
                "message": f"{count} vehicles currently inside the gate",
            }
        )
    return alerts


def build_dashboard_stats(start_date, end_date, period_meta):
    inward_qs = _inward_period_qs(start_date, end_date)
    invoice_qs = _invoice_period_qs(start_date, end_date)
    po_qs = _po_period_qs(start_date, end_date)

    kpis = _build_kpis(inward_qs, invoice_qs, po_qs, start_date, end_date)

    return {
        "period": period_meta,
        "visibility": VISIBILITY,
        "kpis": kpis,
        "charts": {
            "inward_by_status": _build_inward_by_status(inward_qs),
            "inward_by_hour": _build_inward_by_hour(inward_qs, start_date, end_date),
            "daily_comparison": _build_daily_comparison(
                inward_qs, invoice_qs, start_date, end_date
            ),
        },
        "recent": _build_recent(inward_qs, invoice_qs, po_qs),
        "alerts": _build_alerts(kpis),
    }
