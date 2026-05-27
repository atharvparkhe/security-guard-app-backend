from datetime import datetime, timedelta

from django.utils import timezone

from gate.models import InwardEntry, InwardEntryStatusLog, InwardLifecycleStep, StoresAcknowledgment
from gate.services.inward_lifecycle import LIFECYCLE_STEP_ORDER


def _parse_date_param(value, param_name):
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid {param_name} format. Use YYYY-MM-DD.") from exc


def parse_inward_list_date_filter(query_params):
    date_str = query_params.get("date")
    from_str = query_params.get("from_date")
    to_str = query_params.get("to_date")

    if date_str:
        if from_str or to_str:
            raise ValueError("Use either `date` or `from_date`/`to_date`, not both.")
        single = _parse_date_param(date_str, "date")
        return single, single, {"date": single.isoformat()}

    if from_str or to_str:
        if not from_str or not to_str:
            raise ValueError("Both `from_date` and `to_date` are required for a range.")
        start = _parse_date_param(from_str, "from_date")
        end = _parse_date_param(to_str, "to_date")
        if start > end:
            raise ValueError("`from_date` must be on or before `to_date`.")
        return start, end, {"from_date": start.isoformat(), "to_date": end.isoformat()}

    today = timezone.localdate()
    return today, today, {"date": today.isoformat()}


def _format_period_label(start_date, end_date):
    if start_date == end_date:
        today = timezone.localdate()
        if start_date == today:
            prefix = "Today"
        elif start_date == today - timedelta(days=1):
            prefix = "Yesterday"
        else:
            prefix = start_date.strftime("%d %b %Y")
        return f"{prefix}, {start_date.strftime('%d %b %Y')}"

    return f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"


def build_period_meta(start_date, end_date):
    if start_date == end_date:
        return {
            "mode": "single_day",
            "date": start_date.isoformat(),
            "from_date": None,
            "to_date": None,
            "label": _format_period_label(start_date, end_date),
            "timezone": timezone.get_current_timezone_name(),
        }
    return {
        "mode": "range",
        "date": None,
        "from_date": start_date.isoformat(),
        "to_date": end_date.isoformat(),
        "label": _format_period_label(start_date, end_date),
        "timezone": timezone.get_current_timezone_name(),
    }


def parse_dashboard_period_filter(query_params):
    """
    Resolve dashboard date range from query params.

    Explicit ``date`` or ``from_date``/``to_date`` override ``period`` shortcuts.
    """
    date_str = query_params.get("date")
    from_str = query_params.get("from_date")
    to_str = query_params.get("to_date")

    if date_str or from_str or to_str:
        start, end, _ = parse_inward_list_date_filter(query_params)
        return start, end, build_period_meta(start, end)

    period = (query_params.get("period") or "today").strip().lower()
    today = timezone.localdate()

    if period == "today":
        start = end = today
    elif period == "yesterday":
        start = end = today - timedelta(days=1)
    elif period == "last_7_days":
        end = today
        start = today - timedelta(days=6)
    elif period == "last_30_days":
        end = today
        start = today - timedelta(days=29)
    else:
        raise ValueError(
            "Invalid period. Use today, yesterday, last_7_days, or last_30_days."
        )

    return start, end, build_period_meta(start, end)


def file_url(request, field):
    if field and hasattr(field, "url"):
        return request.build_absolute_uri(field.url) if request else field.url
    return None


def serialize_invoice(invoice, request):
    vendor_data = None
    if invoice.vendor_id:
        vendor_data = {"id": str(invoice.vendor_id), "name": invoice.vendor.name}

    po_data = None
    if invoice.po_id:
        po_data = {
            "id": str(invoice.po_id),
            "po_number": invoice.po.po_number,
            "status": invoice.po.status,
        }

    return {
        "id": str(invoice.id),
        "supplier_name": invoice.supplier_name,
        "invoice_from": invoice.supplier_name,
        "vendor": vendor_data,
        "invoice_number": invoice.invoice_number,
        "po_number": invoice.po_number,
        "po": po_data,
        "invoice_date": (
            invoice.invoice_date.isoformat() if invoice.invoice_date else None
        ),
        "invoice_due_date": (
            invoice.invoice_due_date.isoformat() if invoice.invoice_due_date else None
        ),
        "invoice_amount": (
            str(invoice.invoice_amount) if invoice.invoice_amount is not None else None
        ),
        "invoice_amount_after_tax": (
            str(invoice.invoice_amount_after_tax)
            if invoice.invoice_amount_after_tax is not None
            else None
        ),
        "invoice_file": file_url(request, invoice.invoice_file),
    }


def _serialize_stores_acknowledgment(ack, request):
    if ack is None:
        return None
    return {
        "id": str(ack.id),
        "received_invoice_hardcopy": ack.hardcopy_received,
        "comments": ack.stores_remarks,
        "grn_number": ack.grn_number,
        "acknowledged_at": ack.acknowledged_at.isoformat(),
        "acknowledged_by": {
            "id": str(ack.acknowledged_by_id),
            "full_name": ack.acknowledged_by.get_full_name()
            or ack.acknowledged_by.username,
        },
    }


def _serialize_lifecycle_steps(entry):
    labels = dict(InwardLifecycleStep.STEP_CHOICES)
    steps = entry.lifecycle_steps.all()
    order = {key: idx for idx, (key, _) in enumerate(LIFECYCLE_STEP_ORDER)}
    sorted_steps = sorted(steps, key=lambda s: order.get(s.step_key, 99))
    return [
        {
            "step_key": step.step_key,
            "label": labels.get(step.step_key, step.step_key),
            "status": step.status,
            "notes": step.notes,
            "completed_at": (
                step.completed_at.isoformat() if step.completed_at else None
            ),
            "completed_by": (
                str(step.completed_by_id) if step.completed_by_id else None
            ),
        }
        for step in sorted_steps
    ]


def serialize_inward_detail(entry, request):
    gt = entry.gate_transaction
    guard = gt.guard
    truck = entry.truck
    driver = entry.driver

    status_logs = InwardEntryStatusLog.objects.filter(inward_entry=entry).select_related(
        "changed_by"
    )
    logs_data = [
        {
            "from_status": log.from_status,
            "to_status": log.to_status,
            "changed_by": log.changed_by.get_full_name() or log.changed_by.username,
            "changed_at": log.changed_at.isoformat(),
        }
        for log in status_logs
    ]

    try:
        ack = entry.stores_acknowledgment
    except StoresAcknowledgment.DoesNotExist:
        ack = None

    grn_number = ack.grn_number if ack else ""

    return {
        "id": str(entry.id),
        "status": entry.status,
        "is_exit_locked": entry.is_exit_locked,
        "truck": {
            "id": str(truck.id),
            "registration_number": truck.registration_number,
            "truck_photo": file_url(request, truck.truck_photo),
            "vehicle_type": truck.vehicle_type,
            "owner_name": truck.owner_name,
            "owner_contact": truck.owner_contact,
        },
        "driver": {
            "id": str(driver.id),
            "name": driver.name,
            "mobile": driver.mobile,
            "licence_number": driver.licence_number,
            "licence_photo": file_url(request, driver.licence_photo),
        },
        "invoice": serialize_invoice(entry.invoice, request),
        "stores_acknowledgment": _serialize_stores_acknowledgment(ack, request),
        "lifecycle_steps": _serialize_lifecycle_steps(entry),
        "gate_transaction": {
            "id": str(gt.id),
            "truck_photo_at_entry": file_url(request, gt.truck_photo_at_entry),
            "number_of_passengers": gt.number_of_passengers,
            "in_time": gt.in_time.isoformat() if gt.in_time else None,
            "out_time": gt.out_time.isoformat() if gt.out_time else None,
            "guard": {
                "id": str(guard.id),
                "full_name": guard.get_full_name() or guard.username,
            },
        },
        "grn_number": grn_number,
        "guard_remarks": entry.guard_remarks,
        "status_logs": logs_data,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def serialize_invoice_list_item(invoice, request):
    inward_entry_id = None
    entry = invoice.inward_entries.order_by("-created_at").first()
    if entry:
        inward_entry_id = str(entry.id)

    return {
        "id": str(invoice.id),
        "supplier_name": invoice.supplier_name,
        "invoice_from": invoice.supplier_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": (
            invoice.invoice_date.isoformat() if invoice.invoice_date else None
        ),
        "invoice_amount": (
            str(invoice.invoice_amount) if invoice.invoice_amount is not None else None
        ),
        "po_number": invoice.po_number,
        "inward_entry_id": inward_entry_id,
        "created_at": invoice.created_at.isoformat(),
    }


def serialize_inward_list_item(entry, request):
    gt = entry.gate_transaction
    guard = gt.guard
    invoice = entry.invoice

    grn_number = ""
    hardcopy_received = None
    try:
        ack = entry.stores_acknowledgment
        grn_number = ack.grn_number
        hardcopy_received = ack.hardcopy_received
    except StoresAcknowledgment.DoesNotExist:
        pass

    po_number = invoice.po_number or (
        invoice.po.po_number if invoice.po_id else None
    )

    return {
        "id": str(entry.id),
        "status": entry.status,
        "is_exit_locked": entry.is_exit_locked,
        "truck_registration_number": entry.truck.registration_number,
        "driver_name": entry.driver.name,
        "supplier_name": invoice.supplier_name,
        "invoice_from": invoice.supplier_name,
        "invoice_number": invoice.invoice_number,
        "po_number": po_number,
        "invoice_file": file_url(request, invoice.invoice_file),
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "out_time": gt.out_time.isoformat() if gt.out_time else None,
        "time_inside_minutes": time_inside_minutes(gt.in_time),
        "grn_number": grn_number,
        "hardcopy_received": hardcopy_received,
        "guard": {
            "id": str(guard.id),
            "full_name": guard.get_full_name() or guard.username,
        },
        "created_at": entry.created_at.isoformat(),
    }


def serialize_inward_list_item_superadmin(entry, request):
    gt = entry.gate_transaction
    invoice = entry.invoice

    stores_manager_acknowledgment = False
    invoice_hardcopy_received = False
    try:
        ack = entry.stores_acknowledgment
        stores_manager_acknowledgment = True
        invoice_hardcopy_received = ack.hardcopy_received
    except StoresAcknowledgment.DoesNotExist:
        pass

    return {
        "id": str(entry.id),
        "client_name": invoice.supplier_name,
        "vehicle_number": entry.truck.registration_number,
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "out_time": gt.out_time.isoformat() if gt.out_time else None,
        "stores_manager_acknowledgment": stores_manager_acknowledgment,
        "invoice_hardcopy_received": invoice_hardcopy_received,
    }


def time_inside_minutes(in_time):
    if not in_time:
        return 0
    return int((timezone.now() - in_time).total_seconds() / 60)


def duration_minutes(in_time, out_time):
    if not in_time or not out_time:
        return 0
    return int((out_time - in_time).total_seconds() / 60)
