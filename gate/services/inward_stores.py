import re

from django.db import transaction

from core.settings import configurations
from gate.models import InwardEntry, StoresAcknowledgment
from gate.services.inward_lifecycle import sync_lifecycle_from_state


def _validate_grn(grn_number):
    if not grn_number:
        return
    if not re.match(configurations.GRN_FORMAT_REGEX, grn_number):
        raise ValueError("Invalid GRN format. Must match GRN/YY-YY/NNN")


def process_stores_acknowledgment_create(entry, user, data):
    if entry.status != InwardEntry.STATUS_PENDING_VERIFICATION:
        raise ValueError(f"Cannot acknowledge entry in status '{entry.status}'")
    try:
        entry.stores_acknowledgment
        raise ValueError("Stores acknowledgment already recorded. Use PATCH to update.")
    except StoresAcknowledgment.DoesNotExist:
        pass

    received_invoice_hardcopy = data["received_invoice_hardcopy"]
    grn_number = (data.get("grn_number") or "").strip()
    _validate_grn(grn_number)

    with transaction.atomic():
        StoresAcknowledgment.objects.create(
            inward_entry=entry,
            hardcopy_received=received_invoice_hardcopy,
            grn_number=grn_number,
            stores_remarks=(data.get("comments") or "").strip(),
            acknowledged_by=user,
        )
        if received_invoice_hardcopy:
            entry.transition_status(
                InwardEntry.STATUS_ACKNOWLEDGED,
                user,
                notes="Invoice hard copy received by stores",
            )
        sync_lifecycle_from_state(entry, user=user)

    return entry


def process_stores_acknowledgment_update(entry, user, data):
    if entry.status == InwardEntry.STATUS_COMPLETED:
        raise ValueError("Cannot update acknowledgment after inward is completed")
    try:
        ack = entry.stores_acknowledgment
    except StoresAcknowledgment.DoesNotExist as exc:
        raise ValueError("No stores acknowledgment exists. Use POST first.") from exc

    if "received_invoice_hardcopy" in data:
        if ack.hardcopy_received and not data["received_invoice_hardcopy"]:
            raise ValueError(
                "Cannot set received_invoice_hardcopy to false after it was true"
            )
        ack.hardcopy_received = data["received_invoice_hardcopy"]

    if "grn_number" in data:
        grn_number = (data.get("grn_number") or "").strip()
        _validate_grn(grn_number)
        ack.grn_number = grn_number

    if "comments" in data:
        ack.stores_remarks = (data.get("comments") or "").strip()

    with transaction.atomic():
        ack.save()
        if (
            ack.hardcopy_received
            and entry.status == InwardEntry.STATUS_PENDING_VERIFICATION
        ):
            entry.transition_status(
                InwardEntry.STATUS_ACKNOWLEDGED,
                user,
                notes="Invoice hard copy received by stores",
            )
        sync_lifecycle_from_state(entry, user=user)

    return entry
