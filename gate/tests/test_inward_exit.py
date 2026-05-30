from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from employee.models import Employee
from gate.models import (
    Driver,
    GateTransaction,
    InwardEntry,
    Invoice,
    StoresAcknowledgment,
    Truck,
)


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def _create_guard(suffix):
    return Employee.objects.create_user(
        username=f"exit_guard_{suffix}",
        password="testpass123",
        employee_id=f"EL{int(suffix) % 1000:03d}",
        role=Employee.ROLE_SECURITY_GUARD,
        first_name="Guard",
        last_name=suffix,
    )


def _create_acknowledged_entry(creator_guard):
    truck = Truck.objects.create(registration_number=f"MH12EX{int(creator_guard.id) % 10000:04d}")
    driver = Driver.objects.create(
        name="Exit Driver",
        mobile=f"92000{int(creator_guard.id) % 100000:05d}",
    )
    invoice = Invoice.objects.create(
        supplier_name="Supplier Co",
        invoice_number="INV-EX-1",
        po_number="PO-EX-1",
    )
    gt = GateTransaction.objects.create(
        truck=truck,
        driver=driver,
        in_time=timezone.now(),
        guard=creator_guard,
    )
    entry = InwardEntry.objects.create(
        gate_transaction=gt,
        truck=truck,
        driver=driver,
        invoice=invoice,
        status=InwardEntry.STATUS_ACKNOWLEDGED,
    )
    StoresAcknowledgment.objects.create(
        inward_entry=entry,
        hardcopy_received=True,
        acknowledged_by=creator_guard,
    )
    return entry


class InwardExitAPITests(TestCase):
    def test_any_guard_can_mark_exit(self):
        creator = _create_guard("301")
        other_guard = _create_guard("302")
        entry = _create_acknowledged_entry(creator)

        response = _auth_client(other_guard).post(
            f"/inward/{entry.id}/mark-exit/",
            {"guard_remarks": "Exited by relief guard"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertEqual(entry.status, InwardEntry.STATUS_COMPLETED)
        self.assertIsNotNone(entry.gate_transaction.out_time)
        self.assertEqual(entry.guard_remarks, "Exited by relief guard")
