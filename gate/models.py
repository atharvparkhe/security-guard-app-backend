from django.db import models

from base.models import BaseModel


class Truck(BaseModel):
    VEHICLE_TYPE_TRUCK = "truck"
    VEHICLE_TYPE_TEMPO = "tempo"
    VEHICLE_TYPE_PICKUP = "pickup"
    VEHICLE_TYPE_VAN = "van"
    VEHICLE_TYPE_TWO_WHEELER = "two_wheeler"
    VEHICLE_TYPE_OTHER = "other"

    VEHICLE_TYPE_CHOICES = [
        (VEHICLE_TYPE_TRUCK, "Truck"),
        (VEHICLE_TYPE_TEMPO, "Tempo"),
        (VEHICLE_TYPE_PICKUP, "Pickup"),
        (VEHICLE_TYPE_VAN, "Van"),
        (VEHICLE_TYPE_TWO_WHEELER, "Two Wheeler"),
        (VEHICLE_TYPE_OTHER, "Other"),
    ]

    registration_number = models.CharField(max_length=20, unique=True)
    truck_photo = models.ImageField(upload_to="trucks/", null=True, blank=True)
    vehicle_type = models.CharField(
        max_length=20,
        choices=VEHICLE_TYPE_CHOICES,
        default=VEHICLE_TYPE_TRUCK,
    )
    owner_name = models.CharField(max_length=200, blank=True)
    owner_contact = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["registration_number"]

    def __str__(self):
        return self.registration_number


class Driver(BaseModel):
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    licence_number = models.CharField(max_length=50, null=True, blank=True)
    licence_photo = models.ImageField(
        upload_to="driver_licences/",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.mobile})"


class GateTransaction(BaseModel):
    TRANSACTION_INWARD = "inward"
    TRANSACTION_OUTWARD = "outward"
    TRANSACTION_RETURNABLE = "returnable"
    TRANSACTION_NON_RETURNABLE = "non_returnable"
    TRANSACTION_VISITOR = "visitor"
    TRANSACTION_COMPANY_VEHICLE = "company_vehicle"

    TRANSACTION_TYPE_CHOICES = [
        (TRANSACTION_INWARD, "Inward"),
        (TRANSACTION_OUTWARD, "Outward"),
        (TRANSACTION_RETURNABLE, "Returnable"),
        (TRANSACTION_NON_RETURNABLE, "Non Returnable"),
        (TRANSACTION_VISITOR, "Visitor"),
        (TRANSACTION_COMPANY_VEHICLE, "Company Vehicle"),
    ]

    truck = models.ForeignKey(
        Truck,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    truck_photo_at_entry = models.ImageField(
        upload_to="gate_photos/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    number_of_passengers = models.PositiveSmallIntegerField(default=0)
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
        default=TRANSACTION_INWARD,
    )
    guard = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="gate_transactions",
    )
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.truck.registration_number} - {self.transaction_type}"


class Invoice(BaseModel):
    supplier_name = models.CharField(max_length=255, blank=True)
    vendor = models.ForeignKey(
        "orders.Vendor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_number = models.CharField(max_length=100, blank=True)
    po_number = models.CharField(max_length=100, blank=True)
    po = models.ForeignKey(
        "orders.PurchaseOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )
    invoice_date = models.DateField(null=True, blank=True)
    invoice_due_date = models.DateField(null=True, blank=True)
    invoice_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    invoice_amount_after_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    invoice_file = models.FileField(
        upload_to="invoices/%Y/%m/%d/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.invoice_number or str(self.id)


class InwardEntry(BaseModel):
    STATUS_PENDING_VERIFICATION = "pending_verification"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING_VERIFICATION, "Pending Verification"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_COMPLETED, "Completed"),
    ]

    VALID_TRANSITIONS = {
        STATUS_PENDING_VERIFICATION: [STATUS_ACKNOWLEDGED],
        STATUS_ACKNOWLEDGED: [STATUS_COMPLETED],
        STATUS_COMPLETED: [],
    }

    gate_transaction = models.OneToOneField(
        GateTransaction,
        on_delete=models.PROTECT,
        related_name="inward_entry",
    )
    truck = models.ForeignKey(
        Truck,
        on_delete=models.PROTECT,
        related_name="inward_entries",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.PROTECT,
        related_name="inward_entries",
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="inward_entries",
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING_VERIFICATION,
    )
    guard_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Inward {self.id} - {self.status}"

    @property
    def in_time(self):
        return self.gate_transaction.in_time

    @property
    def out_time(self):
        return self.gate_transaction.out_time

    @property
    def is_exit_locked(self):
        if self.status != self.STATUS_ACKNOWLEDGED:
            return True
        try:
            return not self.stores_acknowledgment.hardcopy_received
        except StoresAcknowledgment.DoesNotExist:
            return True

    def transition_status(self, new_status, changed_by, notes=""):
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Cannot transition from '{self.status}' to '{new_status}'"
            )
        old_status = self.status
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        InwardEntryStatusLog.objects.create(
            inward_entry=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )


class StoresAcknowledgment(BaseModel):
    inward_entry = models.OneToOneField(
        InwardEntry,
        on_delete=models.CASCADE,
        related_name="stores_acknowledgment",
    )
    hardcopy_received = models.BooleanField(default=False)
    grn_number = models.CharField(max_length=100, blank=True)
    acknowledged_by = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="stores_acknowledgments",
    )
    acknowledged_at = models.DateTimeField(auto_now_add=True)
    stores_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-acknowledged_at"]

    def __str__(self):
        return f"Stores ack {self.inward_entry_id}"


class InwardLifecycleStep(BaseModel):
    STEP_VEHICLE_DRIVER = "vehicle_driver"
    STEP_INVOICE_PHOTO = "invoice_photo"
    STEP_INVOICE_DETAILS = "invoice_details"
    STEP_GATE_IN = "gate_in"
    STEP_STORES_HARDCOPY = "stores_hardcopy"
    STEP_STORES_GRN = "stores_grn"
    STEP_GATE_OUT = "gate_out"

    STEP_CHOICES = [
        (STEP_VEHICLE_DRIVER, "Vehicle & driver"),
        (STEP_INVOICE_PHOTO, "Invoice photo"),
        (STEP_INVOICE_DETAILS, "Invoice header"),
        (STEP_GATE_IN, "Allowed in"),
        (STEP_STORES_HARDCOPY, "Hard copy"),
        (STEP_STORES_GRN, "GRN"),
        (STEP_GATE_OUT, "Exit"),
    ]

    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    inward_entry = models.ForeignKey(
        InwardEntry,
        on_delete=models.CASCADE,
        related_name="lifecycle_steps",
    )
    step_key = models.CharField(max_length=30, choices=STEP_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inward_lifecycle_completions",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["inward_entry", "step_key"],
                name="gate_inwardlifecyclestep_entry_step_unique",
            )
        ]

    def __str__(self):
        return f"{self.inward_entry_id} - {self.step_key} ({self.status})"


class InwardEntryStatusLog(models.Model):
    inward_entry = models.ForeignKey(
        InwardEntry,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    from_status = models.CharField(max_length=30, blank=True)
    to_status = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="inward_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["changed_at"]

    def __str__(self):
        return f"{self.from_status} -> {self.to_status}"


# Future model stubs
class OutwardEntry(BaseModel):
    pass


class ReturnableGatePass(BaseModel):
    pass


class ReturnableGatePassItem(BaseModel):
    pass


class NonReturnableGatePass(BaseModel):
    pass


class NonReturnableGatePassItem(BaseModel):
    pass


class VisitorEntry(BaseModel):
    pass


class VisitorBaggage(BaseModel):
    pass


class CompanyVehicle(BaseModel):
    pass


class CompanyVehicleMovement(BaseModel):
    pass
