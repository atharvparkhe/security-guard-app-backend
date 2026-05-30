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
    TRANSACTION_RETURNABLE_RETURN = "returnable_return"
    TRANSACTION_VISITOR_VEHICLE = "visitor_vehicle"
    # Legacy values (migrated in 0005)
    TRANSACTION_RETURNABLE = "returnable"
    TRANSACTION_NON_RETURNABLE = "non_returnable"
    TRANSACTION_VISITOR = "visitor"
    TRANSACTION_COMPANY_VEHICLE = "company_vehicle"

    TRANSACTION_TYPE_CHOICES = [
        (TRANSACTION_INWARD, "Inward"),
        (TRANSACTION_OUTWARD, "Outward"),
        (TRANSACTION_RETURNABLE_RETURN, "Returnable Return"),
        (TRANSACTION_VISITOR_VEHICLE, "Visitor Vehicle"),
    ]

    STATUS_CREATED = "created"
    STATUS_INSIDE = "inside"
    STATUS_EXITED = "exited"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_INSIDE, "Inside"),
        (STATUS_EXITED, "Exited"),
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
        max_length=30,
        choices=TRANSACTION_TYPE_CHOICES,
        default=TRANSACTION_INWARD,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
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


class InwardMaterialItem(BaseModel):
    inward_entry = models.ForeignKey(
        "InwardEntry",
        on_delete=models.CASCADE,
        related_name="material_items",
    )
    description = models.TextField()
    quantity = models.CharField(max_length=50)
    unit = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description[:50]} ({self.quantity})"


class InwardEntry(BaseModel):
    STATUS_DRAFT = "draft"
    STATUS_INVOICE_UPLOADED = "invoice_uploaded"
    STATUS_PENDING_VERIFICATION = "pending_verification"
    STATUS_GRN_GENERATED = "grn_generated"
    STATUS_REJECTED = "rejected"
    STATUS_COMPLETED = "completed"
    # Legacy alias kept for migrations/tests referencing old name
    STATUS_ACKNOWLEDGED = STATUS_GRN_GENERATED

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_INVOICE_UPLOADED, "Invoice Uploaded"),
        (STATUS_PENDING_VERIFICATION, "Pending Verification"),
        (STATUS_GRN_GENERATED, "GRN Generated"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_COMPLETED, "Completed"),
    ]

    VALID_TRANSITIONS = {
        STATUS_DRAFT: [STATUS_INVOICE_UPLOADED],
        STATUS_INVOICE_UPLOADED: [STATUS_PENDING_VERIFICATION],
        STATUS_PENDING_VERIFICATION: [STATUS_GRN_GENERATED, STATUS_REJECTED],
        STATUS_GRN_GENERATED: [STATUS_COMPLETED],
        STATUS_REJECTED: [STATUS_COMPLETED],
        STATUS_COMPLETED: [],
    }

    gate_transaction = models.ForeignKey(
        GateTransaction,
        on_delete=models.PROTECT,
        related_name="inward_entries",
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
        default=STATUS_DRAFT,
    )
    guard_remarks = models.TextField(blank=True)
    rejection_category = models.CharField(max_length=50, blank=True)
    rejection_reason = models.TextField(blank=True)

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
        return self.status in (
            self.STATUS_DRAFT,
            self.STATUS_INVOICE_UPLOADED,
            self.STATUS_PENDING_VERIFICATION,
        )

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
    REJECTION_DAMAGED = "damaged"
    REJECTION_WRONG_MATERIAL = "wrong_material"
    REJECTION_QTY_MISMATCH = "qty_mismatch"
    REJECTION_QUALITY_FAILURE = "quality_failure"
    REJECTION_WRONG_PO = "wrong_po"
    REJECTION_OTHER = "other"

    REJECTION_CATEGORY_CHOICES = [
        (REJECTION_DAMAGED, "Damaged"),
        (REJECTION_WRONG_MATERIAL, "Wrong Material"),
        (REJECTION_QTY_MISMATCH, "Quantity Mismatch"),
        (REJECTION_QUALITY_FAILURE, "Quality Failure"),
        (REJECTION_WRONG_PO, "Wrong PO"),
        (REJECTION_OTHER, "Other"),
    ]

    inward_entry = models.OneToOneField(
        InwardEntry,
        on_delete=models.CASCADE,
        related_name="stores_acknowledgment",
    )
    hardcopy_received = models.BooleanField(default=False)
    grn_number = models.CharField(max_length=100, blank=True)
    rejection_category = models.CharField(
        max_length=30,
        choices=REJECTION_CATEGORY_CHOICES,
        blank=True,
    )
    rejection_reason = models.TextField(blank=True)
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


class OutwardEntry(BaseModel):
    TYPE_STANDARD = "standard"
    TYPE_RETURNABLE = "returnable"
    TYPE_NON_RETURNABLE = "non_returnable"

    TYPE_CHOICES = [
        (TYPE_STANDARD, "Standard"),
        (TYPE_RETURNABLE, "Returnable"),
        (TYPE_NON_RETURNABLE, "Non Returnable"),
    ]

    STATUS_CREATED = "created"
    STATUS_INSIDE = "inside"
    STATUS_COMPLETED = "completed"
    STATUS_PENDING_RETURN = "pending_return"
    STATUS_RETURNED = "returned"
    STATUS_PARTIALLY_RETURNED = "partially_returned"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_INSIDE, "Inside"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_PENDING_RETURN, "Pending Return"),
        (STATUS_RETURNED, "Returned"),
        (STATUS_PARTIALLY_RETURNED, "Partially Returned"),
    ]

    gate_transaction = models.ForeignKey(
        GateTransaction,
        on_delete=models.PROTECT,
        related_name="outward_entries",
    )
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    document_photo = models.ImageField(upload_to="outward_docs/%Y/%m/%d/")
    document_number = models.CharField(max_length=100)
    party_name = models.CharField(max_length=255)
    expected_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )
    guard = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="outward_entries",
    )
    guard_remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Outward {self.document_number} ({self.type})"


class OutwardItem(BaseModel):
    outward_entry = models.ForeignKey(
        OutwardEntry,
        on_delete=models.CASCADE,
        related_name="items",
    )
    description = models.TextField()
    quantity = models.CharField(max_length=50)
    unit = models.CharField(max_length=20, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description[:50]}"


class ReturnableReturn(BaseModel):
    CONDITION_GOOD = "good"
    CONDITION_DAMAGED = "damaged"
    CONDITION_PARTIAL = "partial"

    CONDITION_CHOICES = [
        (CONDITION_GOOD, "Good"),
        (CONDITION_DAMAGED, "Damaged"),
        (CONDITION_PARTIAL, "Partial"),
    ]

    STATUS_CREATED = "created"
    STATUS_INSIDE = "inside"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_INSIDE, "Inside"),
        (STATUS_COMPLETED, "Completed"),
    ]

    gate_transaction = models.ForeignKey(
        GateTransaction,
        on_delete=models.PROTECT,
        related_name="returnable_returns",
    )
    original_outward = models.ForeignKey(
        OutwardEntry,
        on_delete=models.PROTECT,
        related_name="returns",
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    quantity_returned = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )
    guard = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="returnable_returns",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Return for {self.original_outward_id}"


class VisitorEntry(BaseModel):
    ID_PROOF_AADHAR = "aadhar"
    ID_PROOF_PAN = "pan"
    ID_PROOF_PASSPORT = "passport"
    ID_PROOF_DRIVING_LICENCE = "driving_licence"
    ID_PROOF_VOTER_ID = "voter_id"

    ID_PROOF_CHOICES = [
        (ID_PROOF_AADHAR, "Aadhar"),
        (ID_PROOF_PAN, "PAN"),
        (ID_PROOF_PASSPORT, "Passport"),
        (ID_PROOF_DRIVING_LICENCE, "Driving Licence"),
        (ID_PROOF_VOTER_ID, "Voter ID"),
    ]

    STATUS_CREATED = "created"
    STATUS_INSIDE = "inside"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_CREATED, "Created"),
        (STATUS_INSIDE, "Inside"),
        (STATUS_COMPLETED, "Completed"),
    ]

    visitor_name = models.CharField(max_length=200)
    company = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=15)
    id_proof_type = models.CharField(max_length=30, choices=ID_PROOF_CHOICES)
    id_proof_number = models.CharField(max_length=100)
    id_proof_photo = models.ImageField(
        upload_to="visitor_ids/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    purpose = models.TextField()
    reference_employee = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="hosted_visitors",
    )
    vehicle_number = models.CharField(max_length=20, blank=True)
    items_carrying = models.TextField(blank=True)
    nda_signed = models.BooleanField(default=False)
    nda_photo = models.ImageField(
        upload_to="nda_docs/%Y/%m/%d/",
        null=True,
        blank=True,
    )
    in_time = models.DateTimeField(null=True, blank=True)
    out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )
    guard = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="processed_visitors",
    )
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.visitor_name} ({self.status})"
