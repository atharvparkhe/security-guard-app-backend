from django.utils.dateparse import parse_datetime

from rest_framework import serializers


def _non_empty_str(value):
    return value is not None and str(value).strip() != ""


def _resolved_truck_id(attrs):
    truck_id = attrs.get("truck_id")
    vehicle_id = attrs.get("vehicle_id")
    if truck_id and vehicle_id and str(truck_id) != str(vehicle_id):
        raise serializers.ValidationError(
            {
                "vehicle_id": "Must match truck_id when both are sent, or send only one."
            }
        )
    return truck_id or vehicle_id


class InwardCreateSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField()
    driver_id = serializers.UUIDField()
    invoice_image = serializers.ImageField()
    invoice_number = serializers.CharField()
    invoice_from = serializers.CharField()
    po_number = serializers.CharField()
    in_time = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="ISO 8601 arrival time; empty = server now",
    )
    guard_remarks = serializers.CharField(required=False, allow_blank=True)

    def validate_in_time(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if hasattr(value, "isoformat"):
            return value
        parsed = parse_datetime(str(value).strip())
        if parsed is None:
            raise serializers.ValidationError(
                "Invalid in_time. Use ISO format, e.g. 2025-05-20T14:30:00"
            )
        return parsed

    def validate(self, attrs):
        if not _non_empty_str(attrs.get("invoice_number")):
            raise serializers.ValidationError(
                {"invoice_number": "This field is required."}
            )
        if not _non_empty_str(attrs.get("invoice_from")):
            raise serializers.ValidationError({"invoice_from": "This field is required."})
        if not _non_empty_str(attrs.get("po_number")):
            raise serializers.ValidationError({"po_number": "This field is required."})
        truck_id = _resolved_truck_id(attrs)
        if truck_id:
            attrs["truck_id"] = truck_id
            attrs["vehicle_id"] = truck_id
        return attrs


class InwardUpdateSerializer(serializers.Serializer):
    vehicle_id = serializers.UUIDField(required=False)
    driver_id = serializers.UUIDField(required=False)
    invoice_image = serializers.ImageField(required=False)
    invoice_number = serializers.CharField(required=False)
    invoice_from = serializers.CharField(required=False)
    po_number = serializers.CharField(required=False)
    in_time = serializers.CharField(required=False, allow_blank=True)
    guard_remarks = serializers.CharField(required=False, allow_blank=True)

    def validate_in_time(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if hasattr(value, "isoformat"):
            return value
        parsed = parse_datetime(str(value).strip())
        if parsed is None:
            raise serializers.ValidationError("Invalid in_time")
        return parsed

    def validate(self, attrs):
        truck_id = _resolved_truck_id(attrs)
        if truck_id:
            attrs["truck_id"] = truck_id
            attrs["vehicle_id"] = truck_id
        return attrs
