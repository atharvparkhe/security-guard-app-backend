from django.utils.dateparse import parse_datetime
from rest_framework import serializers


class TimeOverrideSerializer(serializers.Serializer):
    in_time = serializers.CharField(required=False, allow_blank=True)
    out_time = serializers.CharField(required=False, allow_blank=True)
    guard_remarks = serializers.CharField(required=False, allow_blank=True)

    def _parse(self, value, field_name):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if hasattr(value, "isoformat"):
            return value
        parsed = parse_datetime(str(value).strip())
        if parsed is None:
            raise serializers.ValidationError(
                {field_name: f"Invalid {field_name}. Use ISO format."}
            )
        return parsed

    def validate_in_time(self, value):
        return self._parse(value, "in_time")

    def validate_out_time(self, value):
        return self._parse(value, "out_time")


class InwardDraftCreateSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField()
    driver_id = serializers.UUIDField()
    number_of_passengers = serializers.IntegerField(required=False, default=0)
    guard_remarks = serializers.CharField(required=False, allow_blank=True, default="")


class InwardConfirmInvoiceSerializer(serializers.Serializer):
    invoice_number = serializers.CharField()
    invoice_from = serializers.CharField()
    po_number = serializers.CharField()
    invoice_date = serializers.DateField(required=False, allow_null=True)
    invoice_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    material_items = serializers.JSONField(required=False)


class InwardApproveSerializer(serializers.Serializer):
    grn_number = serializers.CharField()
    received_invoice_hardcopy = serializers.BooleanField(default=True)
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class InwardRejectSerializer(serializers.Serializer):
    rejection_category = serializers.CharField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
    comments = serializers.CharField(required=False, allow_blank=True, default="")
