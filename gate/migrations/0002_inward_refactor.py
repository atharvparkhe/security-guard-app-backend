# Generated manually for inward gate refactor

import uuid
from decimal import Decimal, InvalidOperation

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def _to_decimal(value, default="0"):
    if value is None or (isinstance(value, str) and not str(value).strip()):
        return Decimal(default)
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return Decimal(default)


def migrate_inward_data(apps, schema_editor):
    InwardEntry = apps.get_model("gate", "InwardEntry")
    InwardItem = apps.get_model("gate", "InwardItem")
    Invoice = apps.get_model("gate", "Invoice")
    InvoiceItem = apps.get_model("gate", "InvoiceItem")
    StoresVerification = apps.get_model("gate", "StoresVerification")

    for entry in InwardEntry.objects.select_related(
        "gate_transaction", "vendor", "po", "stores_person"
    ).iterator():
        gt = entry.gate_transaction
        invoice = Invoice.objects.create(
            supplier_name=entry.vendor_name_raw or "",
            vendor_id=entry.vendor_id,
            invoice_number=entry.invoice_number or "",
            po_number="",
            po_id=entry.po_id,
            invoice_date=entry.invoice_date,
            invoice_amount=entry.invoice_amount,
            invoice_file=entry.invoice_image,
        )
        if entry.po_id and hasattr(entry.po, "po_number"):
            invoice.po_number = entry.po.po_number
            invoice.save(update_fields=["po_number"])

        for old_item in InwardItem.objects.filter(inward_entry_id=entry.id):
            InvoiceItem.objects.create(
                invoice=invoice,
                po_item_id=old_item.po_item_id,
                product_name=old_item.description,
                quantity=_to_decimal(old_item.quantity_invoiced, "0"),
                rate=Decimal("0"),
                unit=old_item.unit or "",
                quantity_received=_to_decimal(old_item.quantity_received)
                if old_item.quantity_received
                else None,
                remarks=old_item.remarks or "",
            )

        entry.truck_id = gt.truck_id
        entry.driver_id = gt.driver_id
        entry.invoice_id = invoice.id
        entry.save(update_fields=["truck_id", "driver_id", "invoice_id", "updated_at"])

        if entry.status in ("grn_generated", "rejected", "completed") and entry.stores_person_id:
            status = (
                "rejected"
                if entry.status == "rejected"
                else "approved"
            )
            StoresVerification.objects.create(
                inward_entry_id=entry.id,
                stores_person_id=entry.stores_person_id or gt.guard_id,
                invoice_received=entry.invoice_received,
                status=status,
                grn_number=entry.grn_number or "",
                stores_remarks=entry.stores_remarks or "",
                rejection_category=entry.rejection_category or "",
                rejection_reason=entry.rejection_reason or "",
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gate", "0001_initial"),
        ("orders", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="truck",
            name="owner_contact",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="driver",
            name="licence_number",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("supplier_name", models.CharField(blank=True, max_length=255)),
                ("invoice_number", models.CharField(blank=True, max_length=100)),
                ("po_number", models.CharField(blank=True, max_length=100)),
                ("invoice_date", models.DateField(blank=True, null=True)),
                ("invoice_due_date", models.DateField(blank=True, null=True)),
                (
                    "invoice_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "invoice_amount_after_tax",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "invoice_file",
                    models.FileField(
                        blank=True, null=True, upload_to="invoices/%Y/%m/%d/"
                    ),
                ),
                (
                    "po",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invoices",
                        to="orders.purchaseorder",
                    ),
                ),
                (
                    "vendor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invoices",
                        to="orders.vendor",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="InvoiceItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("product_name", models.CharField(max_length=500)),
                ("quantity", models.DecimalField(decimal_places=4, max_digits=14)),
                ("rate", models.DecimalField(decimal_places=4, max_digits=14)),
                ("unit", models.CharField(blank=True, max_length=20)),
                (
                    "total_amount",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "total_amount_after_tax",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "quantity_received",
                    models.DecimalField(
                        blank=True, decimal_places=4, max_digits=14, null=True
                    ),
                ),
                ("remarks", models.TextField(blank=True)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="gate.invoice",
                    ),
                ),
                (
                    "po_item",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="invoice_items",
                        to="orders.purchaseorderitem",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddField(
            model_name="inwardentry",
            name="truck",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.truck",
            ),
        ),
        migrations.AddField(
            model_name="inwardentry",
            name="driver",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.driver",
            ),
        ),
        migrations.AddField(
            model_name="inwardentry",
            name="invoice",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.invoice",
            ),
        ),
        migrations.CreateModel(
            name="StoresVerification",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("invoice_received", models.BooleanField(default=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("approved", "Approved"), ("rejected", "Rejected")],
                        max_length=20,
                    ),
                ),
                ("grn_number", models.CharField(blank=True, max_length=100)),
                ("stores_remarks", models.TextField(blank=True)),
                (
                    "rejection_category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("damaged", "Damaged"),
                            ("wrong_material", "Wrong Material"),
                            ("qty_mismatch", "Quantity Mismatch"),
                            ("quality_failure", "Quality Failure"),
                            ("wrong_po", "Wrong PO"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("rejection_reason", models.TextField(blank=True)),
                ("verified_at", models.DateTimeField(auto_now_add=True)),
                (
                    "inward_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stores_verification",
                        to="gate.inwardentry",
                    ),
                ),
                (
                    "stores_person",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores_verifications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-verified_at"]},
        ),
        migrations.RunPython(migrate_inward_data, noop_reverse),
        migrations.AlterField(
            model_name="inwardentry",
            name="truck",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.truck",
            ),
        ),
        migrations.AlterField(
            model_name="inwardentry",
            name="driver",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.driver",
            ),
        ),
        migrations.AlterField(
            model_name="inwardentry",
            name="invoice",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.invoice",
            ),
        ),
        migrations.AlterField(
            model_name="inwardentry",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("invoice_uploaded", "Invoice Uploaded"),
                    ("pending_verification", "Pending Verification"),
                    ("grn_generated", "GRN Generated"),
                    ("rejected", "Rejected"),
                    ("completed", "Completed"),
                ],
                default="pending_verification",
                max_length=30,
            ),
        ),
        migrations.RemoveField(model_name="inwardentry", name="challan_number"),
        migrations.RemoveField(model_name="inwardentry", name="invoice_amount"),
        migrations.RemoveField(model_name="inwardentry", name="invoice_date"),
        migrations.RemoveField(model_name="inwardentry", name="invoice_image"),
        migrations.RemoveField(model_name="inwardentry", name="invoice_number"),
        migrations.RemoveField(model_name="inwardentry", name="invoice_received"),
        migrations.RemoveField(model_name="inwardentry", name="ocr_confidence"),
        migrations.RemoveField(model_name="inwardentry", name="ocr_raw_response"),
        migrations.RemoveField(model_name="inwardentry", name="po"),
        migrations.RemoveField(model_name="inwardentry", name="rejection_category"),
        migrations.RemoveField(model_name="inwardentry", name="rejection_reason"),
        migrations.RemoveField(model_name="inwardentry", name="stores_person"),
        migrations.RemoveField(model_name="inwardentry", name="stores_remarks"),
        migrations.RemoveField(model_name="inwardentry", name="vendor"),
        migrations.RemoveField(model_name="inwardentry", name="vendor_name_raw"),
        migrations.DeleteModel(name="InwardItem"),
    ]
