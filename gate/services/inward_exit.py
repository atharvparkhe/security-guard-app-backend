from django.db import transaction
from django.utils import timezone

from gate.models import InwardEntry, InwardLifecycleStep
from gate.services.inward_create import resolve_in_time
from gate.services.inward_lifecycle import (
    finalize_optional_steps,
    mark_lifecycle_step,
    sync_lifecycle_from_state,
)


def process_exit(entry, user, out_time=None, guard_remarks=None):
    if entry.status != InwardEntry.STATUS_ACKNOWLEDGED:
        raise ValueError(f"Cannot mark exit in status '{entry.status}'")
    if entry.is_exit_locked:
        raise ValueError("Cannot mark exit until stores confirms hard copy received.")

    gt = entry.gate_transaction
    with transaction.atomic():
        gt.out_time = resolve_in_time(out_time) if out_time else timezone.now()
        gt.save(update_fields=["out_time", "updated_at"])

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
        sync_lifecycle_from_state(entry, user=user)

        entry.transition_status(
            InwardEntry.STATUS_COMPLETED,
            user,
            notes="Truck marked exit by guard",
        )

    return gt
