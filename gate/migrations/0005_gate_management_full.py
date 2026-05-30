# Gate management: 6-state inward, full outward/visitor/returnable models

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_inward_statuses(apps, schema_editor):
    InwardEntry = apps.get_model("gate", "InwardEntry")
    status_map = {
        "acknowledged": "grn_generated",
        "pending_verification": "pending_verification",
        "completed": "completed",
        "draft": "draft",
        "invoice_uploaded": "invoice_uploaded",
        "grn_generated": "grn_generated",
        "rejected": "rejected",
    }
    for entry in InwardEntry.objects.all().iterator():
        new_status = status_map.get(entry.status, "pending_verification")
        if entry.status != new_status:
            InwardEntry.objects.filter(pk=entry.pk).update(status=new_status)


def migrate_gate_transaction_status(apps, schema_editor):
    GateTransaction = apps.get_model("gate", "GateTransaction")
    for gt in GateTransaction.objects.all().iterator():
        if gt.out_time:
            status = "exited"
        elif gt.in_time:
            status = "inside"
        else:
            status = "created"
        GateTransaction.objects.filter(pk=gt.pk).update(status=status)


def migrate_transaction_types(apps, schema_editor):
    GateTransaction = apps.get_model("gate", "GateTransaction")
    type_map = {
        "returnable": "outward",
        "non_returnable": "outward",
        "visitor": "visitor_vehicle",
        "company_vehicle": "visitor_vehicle",
    }
    for gt in GateTransaction.objects.all().iterator():
        new_type = type_map.get(gt.transaction_type, gt.transaction_type)
        if new_type not in ("inward", "outward", "returnable_return", "visitor_vehicle"):
            new_type = "inward"
        if gt.transaction_type != new_type:
            GateTransaction.objects.filter(pk=gt.pk).update(transaction_type=new_type)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gate", "0004_align_inward_status_choices"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name="CompanyVehicle"),
        migrations.DeleteModel(name="CompanyVehicleMovement"),
        migrations.DeleteModel(name="NonReturnableGatePassItem"),
        migrations.DeleteModel(name="NonReturnableGatePass"),
        migrations.DeleteModel(name="ReturnableGatePassItem"),
        migrations.DeleteModel(name="ReturnableGatePass"),
        migrations.DeleteModel(name="VisitorBaggage"),
        migrations.DeleteModel(name="OutwardEntry"),
        migrations.DeleteModel(name="VisitorEntry"),
        migrations.AddField(
            model_name="gatetransaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("inside", "Inside"),
                    ("exited", "Exited"),
                ],
                default="created",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="gatetransaction",
            name="transaction_type",
            field=models.CharField(
                choices=[
                    ("inward", "Inward"),
                    ("outward", "Outward"),
                    ("returnable_return", "Returnable Return"),
                    ("visitor_vehicle", "Visitor Vehicle"),
                ],
                default="inward",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="inwardentry",
            name="rejection_category",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="inwardentry",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="storesacknowledgment",
            name="rejection_category",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name="storesacknowledgment",
            name="rejection_reason",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="inwardentry",
            name="gate_transaction",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inward_entries",
                to="gate.gatetransaction",
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
                default="draft",
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="InwardMaterialItem",
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
                ("description", models.TextField()),
                ("quantity", models.CharField(max_length=50)),
                ("unit", models.CharField(blank=True, max_length=20)),
                (
                    "inward_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="material_items",
                        to="gate.inwardentry",
                    ),
                ),
            ],
            options={"abstract": False, "ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="OutwardEntry",
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
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("standard", "Standard"),
                            ("returnable", "Returnable"),
                            ("non_returnable", "Non Returnable"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "document_photo",
                    models.ImageField(upload_to="outward_docs/%Y/%m/%d/"),
                ),
                ("document_number", models.CharField(max_length=100)),
                ("party_name", models.CharField(max_length=255)),
                ("expected_return_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("inside", "Inside"),
                            ("completed", "Completed"),
                            ("pending_return", "Pending Return"),
                            ("returned", "Returned"),
                            ("partially_returned", "Partially Returned"),
                        ],
                        default="created",
                        max_length=30,
                    ),
                ),
                ("guard_remarks", models.TextField(blank=True)),
                (
                    "gate_transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outward_entries",
                        to="gate.gatetransaction",
                    ),
                ),
                (
                    "guard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outward_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False, "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="OutwardItem",
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
                ("description", models.TextField()),
                ("quantity", models.CharField(max_length=50)),
                ("unit", models.CharField(blank=True, max_length=20)),
                ("remarks", models.TextField(blank=True)),
                (
                    "outward_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="gate.outwardentry",
                    ),
                ),
            ],
            options={"abstract": False, "ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="ReturnableReturn",
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
                (
                    "condition",
                    models.CharField(
                        choices=[
                            ("good", "Good"),
                            ("damaged", "Damaged"),
                            ("partial", "Partial"),
                        ],
                        max_length=20,
                    ),
                ),
                ("quantity_returned", models.CharField(max_length=50)),
                ("remarks", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("inside", "Inside"),
                            ("completed", "Completed"),
                        ],
                        default="created",
                        max_length=20,
                    ),
                ),
                (
                    "gate_transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="returnable_returns",
                        to="gate.gatetransaction",
                    ),
                ),
                (
                    "guard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="returnable_returns",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "original_outward",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="returns",
                        to="gate.outwardentry",
                    ),
                ),
            ],
            options={"abstract": False, "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="VisitorEntry",
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
                ("visitor_name", models.CharField(max_length=200)),
                ("company", models.CharField(blank=True, max_length=200)),
                ("phone", models.CharField(max_length=15)),
                (
                    "id_proof_type",
                    models.CharField(
                        choices=[
                            ("aadhar", "Aadhar"),
                            ("pan", "PAN"),
                            ("passport", "Passport"),
                            ("driving_licence", "Driving Licence"),
                            ("voter_id", "Voter ID"),
                        ],
                        max_length=30,
                    ),
                ),
                ("id_proof_number", models.CharField(max_length=100)),
                (
                    "id_proof_photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="visitor_ids/%Y/%m/%d/"
                    ),
                ),
                ("purpose", models.TextField()),
                ("vehicle_number", models.CharField(blank=True, max_length=20)),
                ("items_carrying", models.TextField(blank=True)),
                ("nda_signed", models.BooleanField(default=False)),
                (
                    "nda_photo",
                    models.ImageField(
                        blank=True, null=True, upload_to="nda_docs/%Y/%m/%d/"
                    ),
                ),
                ("in_time", models.DateTimeField(blank=True, null=True)),
                ("out_time", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("inside", "Inside"),
                            ("completed", "Completed"),
                        ],
                        default="created",
                        max_length=20,
                    ),
                ),
                ("remarks", models.TextField(blank=True)),
                (
                    "guard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="processed_visitors",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reference_employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="hosted_visitors",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"abstract": False, "ordering": ["-created_at"]},
        ),
        migrations.RunPython(migrate_gate_transaction_status, noop),
        migrations.RunPython(migrate_transaction_types, noop),
        migrations.RunPython(migrate_inward_statuses, noop),
    ]
