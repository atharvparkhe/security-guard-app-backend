from django.core.files.uploadedfile import SimpleUploadedFile
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
    OutwardEntry,
    Truck,
    VisitorEntry,
)


def _auth(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}"
    )
    return client


def _guard(suffix="401"):
    return Employee.objects.create_user(
        username=f"flow_guard_{suffix}",
        password="testpass123",
        employee_id=f"EL{int(suffix) % 1000:03d}",
        role=Employee.ROLE_SECURITY_GUARD,
        email=f"guard{suffix}@example.com",
    )


class GateFlowTests(TestCase):
    def test_visitor_allow_in_without_nda_returns_400(self):
        guard = _guard("402")
        host = Employee.objects.create_user(
            username="host_402",
            password="testpass123",
            employee_id="EL902",
            role=Employee.ROLE_HR,
            email="host902@example.com",
        )
        entry = VisitorEntry.objects.create(
            visitor_name="Test Visitor",
            phone="9000000001",
            id_proof_type=VisitorEntry.ID_PROOF_AADHAR,
            id_proof_number="1234",
            purpose="Meeting",
            reference_employee=host,
            nda_signed=False,
            nda_photo=SimpleUploadedFile("nda.jpg", b"x"),
            guard=guard,
        )
        response = _auth(guard).post(f"/visitors/{entry.id}/allow-in/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outward_create_requires_document_photo(self):
        guard = _guard("403")
        truck = Truck.objects.create(registration_number="MH12OW403")
        driver = Driver.objects.create(name="OW Driver", mobile="9000000403")
        gt = GateTransaction.objects.create(
            truck=truck,
            driver=driver,
            guard=guard,
            transaction_type=GateTransaction.TRANSACTION_OUTWARD,
        )
        response = _auth(guard).post(
            "/outward/",
            {
                "gate_transaction_id": str(gt.id),
                "type": OutwardEntry.TYPE_STANDARD,
                "document_number": "DOC-1",
                "party_name": "Party A",
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
