from rest_framework import serializers


class StoresAcknowledgmentCreateSerializer(serializers.Serializer):
    received_invoice_hardcopy = serializers.BooleanField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")
    grn_number = serializers.CharField(required=False, allow_blank=True, default="")


class StoresAcknowledgmentUpdateSerializer(serializers.Serializer):
    received_invoice_hardcopy = serializers.BooleanField(required=False)
    comments = serializers.CharField(required=False, allow_blank=True)
    grn_number = serializers.CharField(required=False, allow_blank=True)
