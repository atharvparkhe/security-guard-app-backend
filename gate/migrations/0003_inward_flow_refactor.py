# Inward flow refactor: StoresAcknowledgment, lifecycle steps, remove line items

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


LIFECYCLE_STEP_ORDER = [
    ("vehicle_driver", "Vehicle & driver"),
    ("invoice_photo", "Invoice photo"),
    ("invoice_details", "Invoice header"),
    ("gate_in", "Allowed in"),
    ("stores_hardcopy", "Hard copy"),
    ("stores_grn", "GRN"),
    ("gate_out", "Exit"),
]


def _bootstrap_lifecycle_steps(InwardLifecycleStep, entry, user_id=None):
    for step_key, _label in LIFECYCLE_STEP_ORDER:
        InwardLifecycleStep.objects.get_or_create(
            inward_entry_id=entry.id,
            step_key=step_key,
            defaults={"status": "pending"},
        )


def _sync_lifecycle_from_state(apps, entry):
    InwardLifecycleStep = apps.get_model("gate", "InwardLifecycleStep")
    StoresAcknowledgment = apps.get_model("gate", "StoresAcknowledgment")

    invoice = entry.invoice
    gt = entry.gate_transaction

    def _set(step_key, status):
        InwardLifecycleStep.objects.filter(
            inward_entry_id=entry.id, step_key=step_key
        ).update(status=status)

    if entry.truck_id and entry.driver_id:
        _set("vehicle_driver", "completed")
    if invoice.invoice_file:
        _set("invoice_photo", "completed")
    if (
        (invoice.invoice_number or "").strip()
        and (invoice.supplier_name or "").strip()
        and (invoice.po_number or "").strip()
    ):
        _set("invoice_details", "completed")
    if gt.in_time:
        _set("gate_in", "completed")
    if gt.out_time:
        _set("gate_out", "completed")

    try:
        ack = StoresAcknowledgment.objects.get(inward_entry_id=entry.id)
    except StoresAcknowledgment.DoesNotExist:
        ack = None

    if ack and ack.hardcopy_received:
        _set("stores_hardcopy", "completed")
    if ack and (ack.grn_number or "").strip():
        _set("stores_grn", "completed")
    elif entry.status == "completed" and ack and not (ack.grn_number or "").strip():
        _set("stores_grn", "skipped")


def migrate_inward_flow_data(apps, schema_editor):
    InwardEntry = apps.get_model("gate", "InwardEntry")
    StoresVerification = apps.get_model("gate", "StoresVerification")
    StoresAcknowledgment = apps.get_model("gate", "StoresAcknowledgment")
    InvoiceItem = apps.get_model("gate", "InvoiceItem")

    status_map = {
        "grn_generated": "acknowledged",
        "rejected": "acknowledged",
        "draft": "pending_verification",
        "invoice_uploaded": "pending_verification",
    }

    for entry in InwardEntry.objects.select_related(
        "gate_transaction", "invoice"
    ).iterator():
        new_status = status_map.get(entry.status, entry.status)
        if new_status not in ("pending_verification", "acknowledged", "completed"):
            new_status = "pending_verification"
        if entry.status != new_status:
            InwardEntry.objects.filter(pk=entry.pk).update(status=new_status)

        grn_on_entry = getattr(entry, "grn_number", "") or ""
        try:
            verification = StoresVerification.objects.get(inward_entry_id=entry.id)
        except StoresVerification.DoesNotExist:
            verification = None

        if verification:
            hardcopy = verification.invoice_received or verification.status == "approved"
            grn_number = verification.grn_number or grn_on_entry
            StoresAcknowledgment.objects.create(
                inward_entry_id=entry.id,
                hardcopy_received=hardcopy,
                grn_number=grn_number,
                acknowledged_by_id=verification.stores_person_id,
                acknowledged_at=verification.verified_at,
                stores_remarks=verification.stores_remarks or "",
            )
        elif grn_on_entry:
            StoresAcknowledgment.objects.create(
                inward_entry_id=entry.id,
                hardcopy_received=True,
                grn_number=grn_on_entry,
                acknowledged_by_id=entry.gate_transaction.guard_id,
                acknowledged_at=timezone.now(),
                stores_remarks="",
            )

        _bootstrap_lifecycle_steps(
            apps.get_model("gate", "InwardLifecycleStep"), entry
        )
        entry.refresh_from_db()
        _sync_lifecycle_from_state(apps, entry)

    InvoiceItem.objects.all().delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("gate", "0002_inward_refactor"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="StoresAcknowledgment",
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
                ("hardcopy_received", models.BooleanField(default=False)),
                ("grn_number", models.CharField(blank=True, max_length=100)),
                ("acknowledged_at", models.DateTimeField(auto_now_add=True)),
                ("stores_remarks", models.TextField(blank=True)),
                (
                    "acknowledged_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stores_acknowledgments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "inward_entry",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stores_acknowledgment",
                        to="gate.inwardentry",
                    ),
                ),
            ],
            options={"ordering": ["-acknowledged_at"]},
        ),
        migrations.CreateModel(
            name="InwardLifecycleStep",
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
                    "step_key",
                    models.CharField(
                        choices=[
                            ("vehicle_driver", "Vehicle & driver"),
                            ("invoice_photo", "Invoice photo"),
                            ("invoice_details", "Invoice header"),
                            ("gate_in", "Allowed in"),
                            ("stores_hardcopy", "Hard copy"),
                            ("stores_grn", "GRN"),
                            ("gate_out", "Exit"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("completed", "Completed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="inward_lifecycle_completions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "inward_entry",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_steps",
                        to="gate.inwardentry",
                    ),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="inwardlifecyclestep",
            constraint=models.UniqueConstraint(
                fields=("inward_entry", "step_key"),
                name="gate_inwardlifecyclestep_entry_step_unique",
            ),
        ),
        migrations.RunPython(migrate_inward_flow_data, noop_reverse),
        migrations.RemoveField(model_name="inwardentry", name="grn_number"),
        migrations.RemoveField(model_name="inwardentry", name="grn_date"),
        migrations.AlterField(
            model_name="inwardentry",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("invoice_uploaded", "Invoice Uploaded"),
                    ("pending_verification", "Pending Verification"),
                    ("acknowledged", "Acknowledged"),
                    ("completed", "Completed"),
                ],
                default="pending_verification",
                max_length=30,
            ),
        ),
        migrations.DeleteModel(name="InvoiceItem"),
        migrations.DeleteModel(name="StoresVerification"),
    ]
