from django.db import transaction

from employee.models import Employee
from gate.models import VisitorEntry
from gate.services.gate_time import resolve_gate_time


def process_visitor_create(user, data, files):
    nda_photo = (files or {}).get("nda_photo")
    if not nda_photo:
        raise ValueError("nda_photo is required")

    ref_id = data.get("reference_employee_id")
    try:
        ref = Employee.objects.get(pk=ref_id, is_active=True)
    except Employee.DoesNotExist as exc:
        raise ValueError("Reference employee not found") from exc

    with transaction.atomic():
        entry = VisitorEntry.objects.create(
            visitor_name=(data.get("visitor_name") or "").strip(),
            company=(data.get("company") or "").strip(),
            phone=(data.get("phone") or "").strip(),
            id_proof_type=data.get("id_proof_type"),
            id_proof_number=(data.get("id_proof_number") or "").strip(),
            id_proof_photo=(files or {}).get("id_proof_photo"),
            purpose=(data.get("purpose") or "").strip(),
            reference_employee=ref,
            vehicle_number=(data.get("vehicle_number") or "").strip(),
            items_carrying=(data.get("items_carrying") or "").strip(),
            nda_signed=str(data.get("nda_signed", "")).lower() in ("true", "1", "yes"),
            nda_photo=nda_photo,
            status=VisitorEntry.STATUS_CREATED,
            guard=user,
            remarks=(data.get("remarks") or "").strip(),
        )
    return entry


def process_visitor_allow_in(entry, user, in_time=None):
    if not entry.nda_signed:
        raise ValueError("NDA must be signed before allow in")
    if not entry.nda_photo:
        raise ValueError("NDA photo is required before allow in")
    if entry.status != VisitorEntry.STATUS_CREATED:
        raise ValueError(f"Cannot allow in for status '{entry.status}'")

    with transaction.atomic():
        entry.in_time = resolve_gate_time(in_time)
        entry.status = VisitorEntry.STATUS_INSIDE
        entry.save(update_fields=["in_time", "status", "updated_at"])
    return entry


def process_visitor_mark_exit(entry, user, out_time=None):
    if entry.status != VisitorEntry.STATUS_INSIDE:
        raise ValueError(f"Cannot mark exit for status '{entry.status}'")

    with transaction.atomic():
        entry.out_time = resolve_gate_time(out_time)
        entry.status = VisitorEntry.STATUS_COMPLETED
        entry.save(update_fields=["out_time", "status", "updated_at"])
    return entry
