from rest_framework import serializers

from orders.models import PurchaseOrder, PurchaseOrderItem, Vendor


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "po_number",
            "po_date",
            "vendor_name",
            "status",
        )


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrderItem
        fields = (
            "id",
            "description",
            "quantity_ordered",
            "unit",
            "quantity_received",
        )


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source="vendor.name", read_only=True)
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "po_number",
            "po_date",
            "vendor",
            "vendor_name",
            "total_amount",
            "status",
            "notes",
            "items",
        )
