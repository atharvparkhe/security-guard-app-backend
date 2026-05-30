from datetime import timedelta

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
    Truck,
)
from orders.models import PurchaseOrder, Vendor


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    return client


def _create_employee(role, suffix):
    return Employee.objects.create_user(
        username=f"user_{suffix}",
        password="testpass123",
        employee_id=f"EL{int(suffix) % 1000:03d}",
        role=role,
        first_name="Test",
        last_name=role,
    )


class DashboardStatsAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superadmin = _create_employee(Employee.ROLE_SUPERADMIN, "900")
        cls.guard = _create_employee(Employee.ROLE_SECURITY_GUARD, "901")
        cls.stores = _create_employee(Employee.ROLE_STORES_MANAGER, "902")

        cls.vendor = Vendor.objects.create(name="Acme Supplies")
        cls.truck = Truck.objects.create(registration_number="MH12TEST01")
        cls.driver = Driver.objects.create(
            name="Test Driver",
            mobile="9999999001",
            licence_number="DL-TEST-01",
        )

    def _create_inward(self, guard, inward_status, in_time=None, out_time=None):
        invoice = Invoice.objects.create(
            supplier_name="Acme Supplies",
            invoice_number="INV-TEST-001",
            po_number="PO-001",
        )
        gt = GateTransaction.objects.create(
            truck=self.truck,
            driver=self.driver,
            in_time=in_time,
            out_time=out_time,
            guard=guard,
        )
        return InwardEntry.objects.create(
            gate_transaction=gt,
            truck=self.truck,
            driver=self.driver,
            invoice=invoice,
            status=inward_status,
        )

    def test_superadmin_default_today_success(self):
        self._create_inward(
            self.guard,
            InwardEntry.STATUS_PENDING_VERIFICATION,
            in_time=timezone.now(),
        )
        response = _auth_client(self.superadmin).get("/dashboard/stats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["response_type"], "SUCCESS")
        content = body["content"]
        self.assertEqual(content["period"]["mode"], "single_day")
        self.assertIn("kpis", content)
        self.assertGreaterEqual(content["kpis"]["inward_total"], 1)
        self.assertEqual(len(content["charts"]["inward_by_status"]), 6)
        self.assertEqual(len(content["charts"]["inward_by_hour"]), 24)
        self.assertTrue(content["visibility"]["stores"])

    def test_guard_forbidden(self):
        response = _auth_client(self.guard).get("/dashboard/stats/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_stores_manager_forbidden(self):
        response = _auth_client(self.stores).get("/dashboard/stats/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_date_combo(self):
        response = _auth_client(self.superadmin).get(
            "/dashboard/stats/",
            {"date": "2026-05-20", "from_date": "2026-05-01"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_period_last_7_days(self):
        response = _auth_client(self.superadmin).get(
            "/dashboard/stats/", {"period": "last_7_days"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["content"]["period"]["mode"], "range")

    def test_single_date_query(self):
        today = timezone.localdate().isoformat()
        response = _auth_client(self.superadmin).get(
            "/dashboard/stats/", {"date": today}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["content"]["period"]["date"], today)

    def test_inward_by_hour_empty_for_range(self):
        response = _auth_client(self.superadmin).get(
            "/dashboard/stats/",
            {
                "from_date": "2026-05-01",
                "to_date": "2026-05-07",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["content"]["charts"]["inward_by_hour"], [])

    def test_status_chart_includes_zero_counts(self):
        response = _auth_client(self.superadmin).get("/dashboard/stats/")
        statuses = {
            row["status"] for row in response.json()["content"]["charts"]["inward_by_status"]
        }
        expected = {choice[0] for choice in InwardEntry.STATUS_CHOICES}
        self.assertEqual(statuses, expected)

    def test_recent_arrays_max_ten(self):
        for i in range(12):
            self._create_inward(
                self.guard,
                InwardEntry.STATUS_COMPLETED,
                in_time=timezone.now() - timedelta(hours=i),
                out_time=timezone.now(),
            )
        response = _auth_client(self.superadmin).get("/dashboard/stats/")
        self.assertLessEqual(len(response.json()["content"]["recent"]["inwards"]), 10)

    def test_purchase_order_count_in_period(self):
        PurchaseOrder.objects.create(
            po_number="PO-DASH-001",
            po_date=timezone.localdate(),
            vendor=self.vendor,
            raised_by=self.superadmin,
        )
        response = _auth_client(self.superadmin).get("/dashboard/stats/")
        self.assertGreaterEqual(
            response.json()["content"]["kpis"]["purchase_orders_count"], 1
        )
