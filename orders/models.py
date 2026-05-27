from django.db import models

from base.models import BaseModel


class Vendor(BaseModel):
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PurchaseOrder(BaseModel):
    STATUS_OPEN = "open"
    STATUS_PARTIALLY_RECEIVED = "partially_received"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_PARTIALLY_RECEIVED, "Partially Received"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    po_number = models.CharField(max_length=100, unique=True)
    po_date = models.DateField()
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )
    raised_by = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="raised_purchase_orders",
    )
    notes = models.TextField(blank=True)
    po_document = models.FileField(
        upload_to="purchase_orders/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-po_date", "po_number"]

    def __str__(self):
        return self.po_number


class PurchaseOrderItem(BaseModel):
    po = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    description = models.TextField()
    quantity_ordered = models.CharField(max_length=50)
    unit = models.CharField(max_length=20, blank=True)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quantity_received = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.po.po_number} - {self.description[:50]}"
