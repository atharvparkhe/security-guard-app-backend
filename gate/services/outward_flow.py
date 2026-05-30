import json

from django.db import transaction

from gate.models import GateTransaction, OutwardEntry, OutwardItem
from gate.services.gate_time import resolve_gate_time
from gate.services.inward_create import resolve_driver, resolve_truck


def _parse_items(raw):
    if not raw:
        return []
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def process_outward_create(user, data, files):
    document_photo = (files or {}).get("document_photo")
    if not document_photo:
        raise ValueError("document_photo is required")

    outward_type = data.get("type")
    if outward_type not in dict(OutwardEntry.TYPE_CHOICES):
        raise ValueError("Invalid outward type")

    if outward_type == OutwardEntry.TYPE_RETURNABLE and not data.get("expected_return_date"):
        raise ValueError("expected_return_date is required for returnable outward")

    gate_transaction_id = data.get("gate_transaction_id")
    with transaction.atomic():
        if gate_transaction_id:
            gt = GateTransaction.objects.select_for_update().get(pk=gate_transaction_id)
        else:
            truck, _ = resolve_truck(data, files)
            driver, _ = resolve_driver(data, files)
            gt = GateTransaction.objects.create(
                truck=truck,
                driver=driver,
                truck_photo_at_entry=(files or {}).get("truck_photo_at_entry"),
                number_of_passengers=data.get("number_of_passengers", 0),
                transaction_type=GateTransaction.TRANSACTION_OUTWARD,
                status=GateTransaction.STATUS_CREATED,
                guard=user,
            )

        entry = OutwardEntry.objects.create(
            gate_transaction=gt,
            type=outward_type,
            document_photo=document_photo,
            document_number=(data.get("document_number") or "").strip(),
            party_name=(data.get("party_name") or "").strip(),
            expected_return_date=data.get("expected_return_date"),
            status=OutwardEntry.STATUS_CREATED,
            guard=user,
            guard_remarks=(data.get("guard_remarks") or "").strip(),
        )

        for item in _parse_items(data.get("items")):
            OutwardItem.objects.create(
                outward_entry=entry,
                description=item.get("description", ""),
                quantity=str(item.get("quantity", "")),
                unit=item.get("unit", ""),
                remarks=item.get("remarks", ""),
            )

    return entry


def process_outward_allow_in(entry, user, in_time=None):
    if entry.status != OutwardEntry.STATUS_CREATED:
        raise ValueError(f"Cannot allow in for status '{entry.status}'")
    gt = entry.gate_transaction
    with transaction.atomic():
        gt.in_time = resolve_gate_time(in_time)
        gt.status = GateTransaction.STATUS_INSIDE
        gt.save(update_fields=["in_time", "status", "updated_at"])
        entry.status = OutwardEntry.STATUS_INSIDE
        entry.save(update_fields=["status", "updated_at"])
    return entry


def process_outward_mark_exit(entry, user, out_time=None):
    if entry.status != OutwardEntry.STATUS_INSIDE:
        raise ValueError(f"Cannot mark exit for status '{entry.status}'")
    gt = entry.gate_transaction
    with transaction.atomic():
        gt.out_time = resolve_gate_time(out_time)
        gt.status = GateTransaction.STATUS_EXITED
        gt.save(update_fields=["out_time", "status", "updated_at"])
        if entry.type == OutwardEntry.TYPE_RETURNABLE:
            entry.status = OutwardEntry.STATUS_PENDING_RETURN
        else:
            entry.status = OutwardEntry.STATUS_COMPLETED
        entry.save(update_fields=["status", "updated_at"])
    return entry
