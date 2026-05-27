from django.utils import timezone

from gate.models import InwardEntry, InwardLifecycleStep, StoresAcknowledgment

LIFECYCLE_STEP_ORDER = [
    (InwardLifecycleStep.STEP_VEHICLE_DRIVER, "Vehicle & driver"),
    (InwardLifecycleStep.STEP_INVOICE_PHOTO, "Invoice photo"),
    (InwardLifecycleStep.STEP_INVOICE_DETAILS, "Invoice header"),
    (InwardLifecycleStep.STEP_GATE_IN, "Allowed in"),
    (InwardLifecycleStep.STEP_STORES_HARDCOPY, "Hard copy"),
    (InwardLifecycleStep.STEP_STORES_GRN, "GRN"),
    (InwardLifecycleStep.STEP_GATE_OUT, "Exit"),
]

STEP_CHOICES = InwardLifecycleStep.STEP_CHOICES


def bootstrap_lifecycle_steps(entry, user=None):
    for step_key, _label in LIFECYCLE_STEP_ORDER:
        InwardLifecycleStep.objects.get_or_create(
            inward_entry=entry,
            step_key=step_key,
            defaults={"status": InwardLifecycleStep.STATUS_PENDING},
        )
    sync_lifecycle_from_state(entry, user=user)


def mark_lifecycle_step(entry, step_key, status, user=None, notes=""):
    valid_statuses = {
        InwardLifecycleStep.STATUS_PENDING,
        InwardLifecycleStep.STATUS_COMPLETED,
        InwardLifecycleStep.STATUS_SKIPPED,
    }
    if status not in valid_statuses:
        raise ValueError(f"Invalid lifecycle status: {status}")

    step, _created = InwardLifecycleStep.objects.get_or_create(
        inward_entry=entry,
        step_key=step_key,
        defaults={"status": InwardLifecycleStep.STATUS_PENDING},
    )
    step.status = status
    step.notes = notes or step.notes
    if status == InwardLifecycleStep.STATUS_COMPLETED:
        step.completed_by = user
        step.completed_at = timezone.now()
    elif status == InwardLifecycleStep.STATUS_PENDING:
        step.completed_by = None
        step.completed_at = None
    step.save(
        update_fields=[
            "status",
            "notes",
            "completed_by",
            "completed_at",
            "updated_at",
        ]
    )
    return step


def _non_empty(value):
    return value is not None and str(value).strip() != ""


def sync_lifecycle_from_state(entry, user=None):
    invoice = entry.invoice
    gt = entry.gate_transaction

    if entry.truck_id and entry.driver_id:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_VEHICLE_DRIVER,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    if invoice.invoice_file:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_INVOICE_PHOTO,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    if (
        _non_empty(invoice.invoice_number)
        and _non_empty(invoice.supplier_name)
        and _non_empty(invoice.po_number)
    ):
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_INVOICE_DETAILS,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    if gt.in_time:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_GATE_IN,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    if gt.out_time:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_GATE_OUT,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    try:
        ack = entry.stores_acknowledgment
    except StoresAcknowledgment.DoesNotExist:
        ack = None

    if ack and ack.hardcopy_received:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_STORES_HARDCOPY,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )

    if ack and _non_empty(ack.grn_number):
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_STORES_GRN,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=user,
        )


def finalize_optional_steps(entry):
    grn_step = InwardLifecycleStep.objects.filter(
        inward_entry=entry,
        step_key=InwardLifecycleStep.STEP_STORES_GRN,
        status=InwardLifecycleStep.STATUS_PENDING,
    ).first()
    if grn_step:
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_STORES_GRN,
            InwardLifecycleStep.STATUS_SKIPPED,
        )


def lifecycle_steps_for_entry(entry):
    steps = {
        s.step_key: s
        for s in InwardLifecycleStep.objects.filter(inward_entry=entry)
    }
    order = {key: idx for idx, (key, _) in enumerate(LIFECYCLE_STEP_ORDER)}
    return sorted(
        steps.values(),
        key=lambda s: order.get(s.step_key, 99),
    )
