from django.contrib import admin, messages
from django.utils.html import format_html

from gate.models import (
    Driver,
    GateTransaction,
    InwardEntry,
    InwardEntryStatusLog,
    InwardLifecycleStep,
    InwardMaterialItem,
    Invoice,
    OutwardEntry,
    OutwardItem,
    ReturnableReturn,
    StoresAcknowledgment,
    Truck,
    VisitorEntry,
)
from gate.services.inward_lifecycle import LIFECYCLE_STEP_ORDER, sync_lifecycle_from_state


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "vehicle_type",
        "owner_name",
        "owner_contact",
        "is_active",
    )
    search_fields = ("registration_number",)


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "mobile", "licence_number", "is_active")
    search_fields = ("name", "mobile", "licence_number")


@admin.register(GateTransaction)
class GateTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "truck",
        "driver",
        "transaction_type",
        "status",
        "in_time",
        "out_time",
    )
    list_filter = ("transaction_type", "status")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "supplier_name", "invoice_date", "created_at")
    search_fields = ("invoice_number", "supplier_name")


class InwardMaterialItemInline(admin.TabularInline):
    model = InwardMaterialItem
    extra = 0


@admin.register(StoresAcknowledgment)
class StoresAcknowledgmentAdmin(admin.ModelAdmin):
    list_display = (
        "inward_entry",
        "hardcopy_received",
        "grn_number",
        "acknowledged_by",
        "acknowledged_at",
    )
    list_filter = ("hardcopy_received",)


class InwardLifecycleStepInline(admin.TabularInline):
    model = InwardLifecycleStep
    extra = 0
    can_delete = False
    readonly_fields = (
        "step_key",
        "status",
        "notes",
        "completed_by",
        "completed_at",
        "created_at",
    )
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InwardEntry)
class InwardEntryAdmin(admin.ModelAdmin):
    list_display = (
        "get_registration_number",
        "status",
        "lifecycle_progress",
        "get_supplier",
        "get_grn_number",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "invoice__invoice_number",
        "stores_acknowledgment__grn_number",
        "invoice__supplier_name",
    )
    raw_id_fields = ("gate_transaction", "truck", "driver", "invoice")
    readonly_fields = ("lifecycle_timeline_display",)
    inlines = [InwardLifecycleStepInline, InwardMaterialItemInline]
    actions = ["resync_lifecycle_steps"]

    @admin.display(description="Registration")
    def get_registration_number(self, obj):
        return obj.truck.registration_number

    @admin.display(description="Supplier")
    def get_supplier(self, obj):
        return obj.invoice.supplier_name

    @admin.display(description="GRN")
    def get_grn_number(self, obj):
        try:
            return obj.stores_acknowledgment.grn_number
        except StoresAcknowledgment.DoesNotExist:
            return ""

    @admin.display(description="Lifecycle")
    def lifecycle_progress(self, obj):
        steps = list(obj.lifecycle_steps.all())
        if not steps:
            return "—"
        completed = sum(
            1 for s in steps if s.status == InwardLifecycleStep.STATUS_COMPLETED
        )
        skipped = sum(
            1 for s in steps if s.status == InwardLifecycleStep.STATUS_SKIPPED
        )
        total = len(LIFECYCLE_STEP_ORDER)
        return f"{completed}/{total} done, {skipped} skipped"

    @admin.display(description="Lifecycle timeline")
    def lifecycle_timeline_display(self, obj):
        if not obj.pk:
            return "Save entry first to see lifecycle."
        labels = dict(LIFECYCLE_STEP_ORDER)
        order = {key: idx for idx, (key, _) in enumerate(LIFECYCLE_STEP_ORDER)}
        steps = sorted(
            obj.lifecycle_steps.all(),
            key=lambda s: order.get(s.step_key, 99),
        )
        rows = []
        for step in steps:
            label = labels.get(step.step_key, step.step_key)
            badge = step.status
            rows.append(f"<li><strong>{label}</strong>: {badge}</li>")
        return format_html("<ul>{}</ul>", format_html("".join(rows)))

    @admin.action(description="Re-sync lifecycle steps from entry state")
    def resync_lifecycle_steps(self, request, queryset):
        count = 0
        for entry in queryset:
            sync_lifecycle_from_state(entry, user=request.user)
            count += 1
        self.message_user(
            request,
            f"Re-synced lifecycle for {count} entr{'y' if count == 1 else 'ies'}.",
            messages.SUCCESS,
        )


@admin.register(InwardLifecycleStep)
class InwardLifecycleStepAdmin(admin.ModelAdmin):
    list_display = ("inward_entry", "step_key", "status", "completed_at")
    list_filter = ("step_key", "status")


@admin.register(InwardEntryStatusLog)
class InwardEntryStatusLogAdmin(admin.ModelAdmin):
    list_display = ("inward_entry", "from_status", "to_status", "changed_by", "changed_at")


class OutwardItemInline(admin.TabularInline):
    model = OutwardItem
    extra = 0


@admin.register(OutwardEntry)
class OutwardEntryAdmin(admin.ModelAdmin):
    list_display = ("document_number", "type", "status", "party_name", "created_at")
    list_filter = ("type", "status")
    inlines = [OutwardItemInline]


@admin.register(ReturnableReturn)
class ReturnableReturnAdmin(admin.ModelAdmin):
    list_display = ("original_outward", "condition", "status", "created_at")
    list_filter = ("status", "condition")


@admin.register(VisitorEntry)
class VisitorEntryAdmin(admin.ModelAdmin):
    list_display = (
        "visitor_name",
        "company",
        "status",
        "nda_signed",
        "in_time",
        "out_time",
    )
    list_filter = ("status", "nda_signed")
