from django.utils.dateparse import parse_datetime

from rest_framework import serializers


class InwardExitSerializer(serializers.Serializer):
    out_time = serializers.CharField(required=False, allow_blank=True)
    guard_remarks = serializers.CharField(required=False, allow_blank=True)

    def validate_out_time(self, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        if hasattr(value, "isoformat"):
            return value
        parsed = parse_datetime(str(value).strip())
        if parsed is None:
            raise serializers.ValidationError("Invalid out_time")
        return parsed
