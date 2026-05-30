from django.db import transaction

from gate.models import GateTransaction, OutwardEntry, ReturnableReturn
from gate.services.gate_time import resolve_gate_time
from gate.services.inward_create import resolve_driver, resolve_truck


def process_returnable_create(user, data, files=None):
    original_id = data.get("original_outward_id")
    try:
        original = OutwardEntry.objects.get(pk=original_id)
    except OutwardEntry.DoesNotExist as exc:
        raise ValueError("Original outward entry not found") from exc

    if original.type != OutwardEntry.TYPE_RETURNABLE:
        raise ValueError("Original outward must be returnable type")
    if original.status != OutwardEntry.STATUS_PENDING_RETURN:
        raise ValueError("Original outward must be in pending_return status")

    gate_transaction_id = data.get("gate_transaction_id")
    with transaction.atomic():
        if gate_transaction_id:
            gt = GateTransaction.objects.get(pk=gate_transaction_id)
        else:
            truck, _ = resolve_truck(data, files or {})
            driver, _ = resolve_driver(data, files or {})
            gt = GateTransaction.objects.create(
                truck=truck,
                driver=driver,
                truck_photo_at_entry=(files or {}).get("truck_photo_at_entry"),
                transaction_type=GateTransaction.TRANSACTION_RETURNABLE_RETURN,
                status=GateTransaction.STATUS_CREATED,
                guard=user,
            )

        ret = ReturnableReturn.objects.create(
            gate_transaction=gt,
            original_outward=original,
            condition=data.get("condition"),
            quantity_returned=str(data.get("quantity_returned", "")),
            remarks=(data.get("remarks") or "").strip(),
            status=ReturnableReturn.STATUS_CREATED,
            guard=user,
        )
    return ret


def process_returnable_allow_in(ret, user, in_time=None):
    if ret.status != ReturnableReturn.STATUS_CREATED:
        raise ValueError(f"Cannot allow in for status '{ret.status}'")
    gt = ret.gate_transaction
    with transaction.atomic():
        gt.in_time = resolve_gate_time(in_time)
        gt.status = GateTransaction.STATUS_INSIDE
        gt.save(update_fields=["in_time", "status", "updated_at"])
        ret.status = ReturnableReturn.STATUS_INSIDE
        ret.save(update_fields=["status", "updated_at"])
    return ret


def process_returnable_mark_exit(ret, user, out_time=None, fully_returned=True):
    if ret.status != ReturnableReturn.STATUS_INSIDE:
        raise ValueError(f"Cannot mark exit for status '{ret.status}'")
    gt = ret.gate_transaction
    with transaction.atomic():
        gt.out_time = resolve_gate_time(out_time)
        gt.status = GateTransaction.STATUS_EXITED
        gt.save(update_fields=["out_time", "status", "updated_at"])
        ret.status = ReturnableReturn.STATUS_COMPLETED
        ret.save(update_fields=["status", "updated_at"])

        original = ret.original_outward
        if fully_returned:
            original.status = OutwardEntry.STATUS_RETURNED
        else:
            original.status = OutwardEntry.STATUS_PARTIALLY_RETURNED
        original.save(update_fields=["status", "updated_at"])
    return ret
