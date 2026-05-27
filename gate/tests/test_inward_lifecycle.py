from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from employee.models import Employee
from gate.models import (
    Driver,
    GateTransaction,
    InwardEntry,
    InwardLifecycleStep,
    Invoice,
    StoresAcknowledgment,
    Truck,
)
from gate.services.inward_lifecycle import (
    bootstrap_lifecycle_steps,
    finalize_optional_steps,
    mark_lifecycle_step,
    sync_lifecycle_from_state,
)


def _create_employee(suffix="100"):
    return Employee.objects.create_user(
        username=f"lifecycle_{suffix}",
        password="testpass123",
        employee_id=f"EL{int(suffix) % 1000:03d}",
        role=Employee.ROLE_SECURITY_GUARD,
        first_name="Life",
        last_name="Cycle",
    )


def _create_entry(guard, invoice_file=True, in_time=None):
    truck = Truck.objects.create(registration_number=f"MH12LC{int(guard.id) % 10000:04d}")
    driver = Driver.objects.create(
        name="LC Driver",
        mobile=f"90000{int(guard.id) % 100000:05d}",
    )
    invoice = Invoice.objects.create(
        supplier_name="Supplier Co",
        invoice_number="INV-LC-1",
        po_number="PO-LC-1",
    )
    if invoice_file:
        invoice.invoice_file.save(
            "test.jpg",
            SimpleUploadedFile("test.jpg", b"fake-image"),
            save=True,
        )
    gt = GateTransaction.objects.create(
        truck=truck,
        driver=driver,
        in_time=in_time or timezone.now(),
        guard=guard,
    )
    return InwardEntry.objects.create(
        gate_transaction=gt,
        truck=truck,
        driver=driver,
        invoice=invoice,
        status=InwardEntry.STATUS_PENDING_VERIFICATION,
    )


class InwardLifecycleTests(TestCase):
    def setUp(self):
        self.guard = _create_employee("101")

    def test_bootstrap_creates_seven_steps(self):
        entry = _create_entry(self.guard)
        bootstrap_lifecycle_steps(entry, user=self.guard)
        steps = entry.lifecycle_steps.all()
        self.assertEqual(steps.count(), 7)
        keys = {s.step_key for s in steps}
        self.assertIn(InwardLifecycleStep.STEP_GATE_OUT, keys)

    def test_sync_marks_guard_steps_completed(self):
        entry = _create_entry(self.guard)
        bootstrap_lifecycle_steps(entry, user=self.guard)
        sync_lifecycle_from_state(entry, user=self.guard)

        for key in (
            InwardLifecycleStep.STEP_VEHICLE_DRIVER,
            InwardLifecycleStep.STEP_INVOICE_PHOTO,
            InwardLifecycleStep.STEP_INVOICE_DETAILS,
            InwardLifecycleStep.STEP_GATE_IN,
        ):
            step = entry.lifecycle_steps.get(step_key=key)
            self.assertEqual(step.status, InwardLifecycleStep.STATUS_COMPLETED)

    def test_finalize_optional_steps_skips_grn(self):
        entry = _create_entry(self.guard)
        bootstrap_lifecycle_steps(entry, user=self.guard)
        finalize_optional_steps(entry)
        grn_step = entry.lifecycle_steps.get(
            step_key=InwardLifecycleStep.STEP_STORES_GRN
        )
        self.assertEqual(grn_step.status, InwardLifecycleStep.STATUS_SKIPPED)

    def test_sync_completes_grn_when_ack_has_number(self):
        entry = _create_entry(self.guard)
        bootstrap_lifecycle_steps(entry, user=self.guard)
        StoresAcknowledgment.objects.create(
            inward_entry=entry,
            hardcopy_received=True,
            grn_number="GRN/25-26/001",
            acknowledged_by=self.guard,
        )
        sync_lifecycle_from_state(entry, user=self.guard)
        grn_step = entry.lifecycle_steps.get(
            step_key=InwardLifecycleStep.STEP_STORES_GRN
        )
        self.assertEqual(grn_step.status, InwardLifecycleStep.STATUS_COMPLETED)

    def test_mark_lifecycle_step_updates_status(self):
        entry = _create_entry(self.guard, invoice_file=False)
        bootstrap_lifecycle_steps(entry, user=self.guard)
        mark_lifecycle_step(
            entry,
            InwardLifecycleStep.STEP_INVOICE_PHOTO,
            InwardLifecycleStep.STATUS_COMPLETED,
            user=self.guard,
        )
        step = entry.lifecycle_steps.get(
            step_key=InwardLifecycleStep.STEP_INVOICE_PHOTO
        )
        self.assertEqual(step.status, InwardLifecycleStep.STATUS_COMPLETED)
        self.assertIsNotNone(step.completed_at)
