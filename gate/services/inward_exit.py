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
    """Legacy exit endpoint — delegates to mark-exit flow."""
    from gate.services.inward_flow import process_mark_exit

    return process_mark_exit(entry, user, out_time=out_time, guard_remarks=guard_remarks)
