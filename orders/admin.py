from django.contrib import admin

from orders.models import PurchaseOrder, PurchaseOrderItem, Vendor


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "gstin", "phone", "is_active")
    search_fields = ("name", "gstin")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "po_date", "vendor", "status", "is_active")
    list_filter = ("status",)
    search_fields = ("po_number",)
    inlines = [PurchaseOrderItemInline]


@admin.register(PurchaseOrderItem)
class PurchaseOrderItemAdmin(admin.ModelAdmin):
    list_display = ("po", "description", "quantity_ordered", "unit")
