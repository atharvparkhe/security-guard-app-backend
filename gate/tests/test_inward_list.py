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


def _create_employee(role, suffix):
    return Employee.objects.create_user(
        username=f"inward_list_{suffix}",
        password="testpass123",
        employee_id=f"EL{int(suffix) % 1000:03d}",
        role=role,
        first_name="Test",
        last_name=role,
    )


def _create_inward(guard, inward_status, reg_suffix="01"):
    truck = Truck.objects.create(
        registration_number=f"MH12IL{reg_suffix}"
    )
    driver = Driver.objects.create(
        name=f"Driver {reg_suffix}",
        mobile=f"91000{reg_suffix}",
    )
    invoice = Invoice.objects.create(
        supplier_name="Supplier Co",
        invoice_number=f"INV-{reg_suffix}",
        po_number=f"PO-{reg_suffix}",
    )
    gt = GateTransaction.objects.create(
        truck=truck,
        driver=driver,
        in_time=timezone.now(),
        guard=guard,
    )
    return InwardEntry.objects.create(
        gate_transaction=gt,
        truck=truck,
        driver=driver,
        invoice=invoice,
        status=inward_status,
    )


class InwardListAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guard_a = _create_employee(Employee.ROLE_SECURITY_GUARD, "201")
        cls.guard_b = _create_employee(Employee.ROLE_SECURITY_GUARD, "202")
        cls.stores = _create_employee(Employee.ROLE_STORES_MANAGER, "203")
        cls.superadmin = _create_employee(Employee.ROLE_SUPERADMIN, "204")

    def test_guard_sees_only_own_entries(self):
        own = _create_inward(self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "A1")
        _create_inward(self.guard_b, InwardEntry.STATUS_PENDING_VERIFICATION, "B1")

        response = _auth_client(self.guard_a).get("/inward/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["content"]
        ids = {e["id"] for e in content["entries"]}
        self.assertEqual(ids, {str(own.id)})
        self.assertIn("total_completed", content["stats"])
        self.assertIn("vehicles_inside", content["stats"])

    def test_stores_sees_all_entries_in_range(self):
        entry_a = _create_inward(
            self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "S1"
        )
        entry_b = _create_inward(
            self.guard_b, InwardEntry.STATUS_ACKNOWLEDGED, "S2"
        )

        response = _auth_client(self.stores).get("/inward/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {e["id"] for e in response.json()["content"]["entries"]}
        self.assertEqual(ids, {str(entry_a.id), str(entry_b.id)})

    def test_superadmin_sees_all_entries_slim_payload(self):
        entry_a = _create_inward(
            self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "AD1"
        )
        _create_inward(self.guard_b, InwardEntry.STATUS_COMPLETED, "AD2")

        response = _auth_client(self.superadmin).get("/inward/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["content"]
        self.assertEqual(len(content["entries"]), 2)
        entry = content["entries"][0]
        self.assertEqual(
            set(entry.keys()),
            {
                "id",
                "client_name",
                "vehicle_number",
                "in_time",
                "out_time",
                "stores_manager_acknowledgment",
                "invoice_hardcopy_received",
            },
        )
        self.assertEqual(entry["client_name"], entry_a.invoice.supplier_name)
        self.assertNotIn("id", entry)

    def test_superadmin_stats(self):
        _create_inward(self.guard_a, InwardEntry.STATUS_COMPLETED, "ST1")
        pending = _create_inward(
            self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "ST2"
        )
        StoresAcknowledgment.objects.create(
            inward_entry=pending,
            hardcopy_received=False,
            grn_number="",
            acknowledged_by=self.stores,
        )

        response = _auth_client(self.superadmin).get("/inward/")
        stats = response.json()["content"]["stats"]
        self.assertEqual(
            set(stats.keys()),
            {"completed", "pending", "pending_grn", "no_invoice_hardcopy"},
        )
        self.assertGreaterEqual(stats["completed"], 1)
        self.assertGreaterEqual(stats["pending"], 1)
        self.assertGreaterEqual(stats["pending_grn"], 1)
        self.assertGreaterEqual(stats["no_invoice_hardcopy"], 1)

    def test_status_filter_pending_verification(self):
        pending = _create_inward(
            self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "P1"
        )
        _create_inward(self.guard_a, InwardEntry.STATUS_ACKNOWLEDGED, "P2")

        response = _auth_client(self.stores).get(
            "/inward/", {"status": InwardEntry.STATUS_PENDING_VERIFICATION}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {e["id"] for e in response.json()["content"]["entries"]}
        self.assertEqual(ids, {str(pending.id)})

    def test_list_entry_includes_full_fields(self):
        _create_inward(self.guard_a, InwardEntry.STATUS_PENDING_VERIFICATION, "F1")
        response = _auth_client(self.guard_a).get("/inward/")
        entry = response.json()["content"]["entries"][0]
        for field in (
            "invoice_from",
            "invoice_number",
            "po_number",
            "invoice_file",
            "time_inside_minutes",
            "guard",
            "hardcopy_received",
        ):
            self.assertIn(field, entry)

    def test_pending_verification_route_removed(self):
        response = _auth_client(self.stores).get("/inward/pending-verification/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
