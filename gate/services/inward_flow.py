import json

from django.db import transaction
from django.utils import timezone

from core.settings import configurations
from gate.models import (
    GateTransaction,
    InwardEntry,
    InwardEntryStatusLog,
    InwardLifecycleStep,
    InwardMaterialItem,
    Invoice,
    StoresAcknowledgment,
)
from gate.services.gate_time import resolve_gate_time
from gate.services.inward_create import (
    create_invoice,
    replace_invoice_header,
    resolve_driver,
    resolve_truck,
    validate_invoice_file,
)
from gate.services.inward_lifecycle import (
    bootstrap_lifecycle_steps,
    finalize_optional_steps,
    mark_lifecycle_step,
    sync_lifecycle_from_state,
)
import re


def _validate_grn(grn_number):
    if not grn_number:
        return
    if not re.match(configurations.GRN_FORMAT_REGEX, grn_number):
        raise ValueError("Invalid GRN format. Must match GRN/YY-YY/NNN")


def _log_status(entry, from_status, to_status, user, notes=""):
    InwardEntryStatusLog.objects.create(
        inward_entry=entry,
        from_status=from_status,
        to_status=to_status,
        changed_by=user,
        notes=notes,
    )


def process_inward_draft_create(user, data, files):
    truck, _ = resolve_truck(data, files)
    driver, _ = resolve_driver(data, files)

    with transaction.atomic():
        invoice = Invoice.objects.create(supplier_name="")
        gt = GateTransaction.objects.create(
            truck=truck,
            driver=driver,
            truck_photo_at_entry=(files or {}).get("truck_photo_at_entry"),
            number_of_passengers=data.get("number_of_passengers", 0),
            transaction_type=GateTransaction.TRANSACTION_INWARD,
            status=GateTransaction.STATUS_CREATED,
            guard=user,
        )
        entry = InwardEntry.objects.create(
            gate_transaction=gt,
            truck=truck,
            driver=driver,
            invoice=invoice,
            status=InwardEntry.STATUS_DRAFT,
            guard_remarks=data.get("guard_remarks", ""),
        )
        _log_status(entry, "", InwardEntry.STATUS_DRAFT, user, "Draft created")
        bootstrap_lifecycle_steps(entry, user=user)

    return entry


def process_upload_invoice(entry, user, invoice_file):
    if entry.status not in (InwardEntry.STATUS_DRAFT, InwardEntry.STATUS_INVOICE_UPLOADED):
        raise ValueError(f"Cannot upload invoice in status '{entry.status}'")
    validate_invoice_file(invoice_file)
    old = entry.status
    with transaction.atomic():
        entry.invoice.invoice_file = invoice_file
        entry.invoice.save(update_fields=["invoice_file", "updated_at"])
        if entry.status == InwardEntry.STATUS_DRAFT:
            entry.status = InwardEntry.STATUS_INVOICE_UPLOADED
            entry.save(update_fields=["status", "updated_at"])
            _log_status(
                entry,
                old,
                InwardEntry.STATUS_INVOICE_UPLOADED,
                user,
                "Invoice uploaded",
            )
        sync_lifecycle_from_state(entry, user=user)
    return entry


def process_confirm_invoice(entry, user, data, files=None):
    if entry.status not in (
        InwardEntry.STATUS_INVOICE_UPLOADED,
        InwardEntry.STATUS_DRAFT,
    ):
        raise ValueError(f"Cannot confirm invoice in status '{entry.status}'")

    invoice_file = (files or {}).get("invoice_image") or (files or {}).get("invoice_file")
    old = entry.status
    with transaction.atomic():
        replace_invoice_header(entry.invoice, data, invoice_file=invoice_file)
        if not entry.invoice.invoice_file:
            raise ValueError("Invoice file is required before confirmation")

        entry.material_items.all().delete()
        items = data.get("material_items") or data.get("items") or []
        if isinstance(items, str):
            items = json.loads(items)
        for item in items:
            entry.material_items.create(
                description=item.get("description", ""),
                quantity=str(item.get("quantity", "")),
                unit=item.get("unit", ""),
            )

        entry.status = InwardEntry.STATUS_PENDING_VERIFICATION
        entry.save(update_fields=["status", "updated_at"])
        _log_status(
            entry,
            old,
            InwardEntry.STATUS_PENDING_VERIFICATION,
            user,
            "Invoice confirmed",
        )
        sync_lifecycle_from_state(entry, user=user)
    return entry


def process_allow_in(entry, user, in_time=None):
    if entry.status not in (
        InwardEntry.STATUS_DRAFT,
        InwardEntry.STATUS_INVOICE_UPLOADED,
        InwardEntry.STATUS_PENDING_VERIFICATION,
        InwardEntry.STATUS_GRN_GENERATED,
        InwardEntry.STATUS_REJECTED,
    ):
        raise ValueError(f"Cannot allow in for status '{entry.status}'")

    gt = entry.gate_transaction
    with transaction.atomic():
        gt.in_time = resolve_gate_time(in_time)
        gt.status = GateTransaction.STATUS_INSIDE
        gt.save(update_fields=["in_time", "status", "updated_at"])
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_GATE_IN,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )
        sync_lifecycle_from_state(entry, user=user)
    return entry


def process_mark_exit(entry, user, out_time=None, guard_remarks=None):
    if entry.is_exit_locked:
        raise ValueError("Cannot mark exit until stores approves or rejects the entry.")
    if entry.status not in (InwardEntry.STATUS_GRN_GENERATED, InwardEntry.STATUS_REJECTED):
        raise ValueError(f"Cannot mark exit in status '{entry.status}'")

    gt = entry.gate_transaction
    old = entry.status
    with transaction.atomic():
        gt.out_time = resolve_gate_time(out_time)
        gt.status = GateTransaction.STATUS_EXITED
        gt.save(update_fields=["out_time", "status", "updated_at"])

        if guard_remarks:
            entry.guard_remarks = guard_remarks
            entry.save(update_fields=["guard_remarks", "updated_at"])

        finalize_optional_steps(entry)
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_GATE_OUT,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )
        entry.status = InwardEntry.STATUS_COMPLETED
        entry.save(update_fields=["status", "updated_at"])
        _log_status(entry, old, InwardEntry.STATUS_COMPLETED, user, "Exit marked")
        sync_lifecycle_from_state(entry, user=user)
    return gt


def process_approve(entry, user, data):
    if entry.status != InwardEntry.STATUS_PENDING_VERIFICATION:
        raise ValueError(f"Cannot approve entry in status '{entry.status}'")

    grn_number = (data.get("grn_number") or "").strip()
    _validate_grn(grn_number)
    received = data.get("received_invoice_hardcopy", True)

    old = entry.status
    with transaction.atomic():
        ack, _ = StoresAcknowledgment.objects.update_or_create(
            inward_entry=entry,
            defaults={
                "hardcopy_received": received,
                "grn_number": grn_number,
                "stores_remarks": (data.get("comments") or "").strip(),
                "acknowledged_by": user,
            },
        )
        entry.status = InwardEntry.STATUS_GRN_GENERATED
        entry.save(update_fields=["status", "updated_at"])
        _log_status(entry, old, InwardEntry.STATUS_GRN_GENERATED, user, "Approved by stores")
        sync_lifecycle_from_state(entry, user=user)
    return entry


def process_reject(entry, user, data):
    if entry.status != InwardEntry.STATUS_PENDING_VERIFICATION:
        raise ValueError(f"Cannot reject entry in status '{entry.status}'")

    category = (data.get("rejection_category") or "").strip()
    reason = (data.get("rejection_reason") or data.get("comments") or "").strip()
    if not category:
        raise ValueError("rejection_category is required")

    old = entry.status
    with transaction.atomic():
        StoresAcknowledgment.objects.update_or_create(
            inward_entry=entry,
            defaults={
                "hardcopy_received": False,
                "grn_number": "",
                "stores_remarks": reason,
                "rejection_category": category,
                "rejection_reason": reason,
                "acknowledged_by": user,
            },
        )
        entry.rejection_category = category
        entry.rejection_reason = reason
        entry.status = InwardEntry.STATUS_REJECTED
        entry.save(
            update_fields=[
                "rejection_category",
                "rejection_reason",
                "status",
                "updated_at",
            ]
        )
        _log_status(entry, old, InwardEntry.STATUS_REJECTED, user, "Rejected by stores")
        sync_lifecycle_from_state(entry, user=user)
    return entry
