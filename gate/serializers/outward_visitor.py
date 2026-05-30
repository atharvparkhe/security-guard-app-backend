from rest_framework import serializers

from gate.models import OutwardEntry, ReturnableReturn, VisitorEntry


class OutwardCreateSerializer(serializers.Serializer):
    gate_transaction_id = serializers.UUIDField(required=False)
    vehicle_id = serializers.UUIDField(required=False)
    driver_id = serializers.UUIDField(required=False)
    type = serializers.ChoiceField(choices=OutwardEntry.TYPE_CHOICES)
    document_number = serializers.CharField()
    party_name = serializers.CharField()
    expected_return_date = serializers.DateField(required=False, allow_null=True)
    guard_remarks = serializers.CharField(required=False, allow_blank=True, default="")
    items = serializers.JSONField(required=False)


class ReturnableReturnCreateSerializer(serializers.Serializer):
    gate_transaction_id = serializers.UUIDField(required=False)
    vehicle_id = serializers.UUIDField(required=False)
    driver_id = serializers.UUIDField(required=False)
    original_outward_id = serializers.UUIDField()
    condition = serializers.ChoiceField(choices=ReturnableReturn.CONDITION_CHOICES)
    quantity_returned = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    fully_returned = serializers.BooleanField(required=False, default=True)


class VisitorCreateSerializer(serializers.Serializer):
    visitor_name = serializers.CharField()
    company = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField()
    id_proof_type = serializers.ChoiceField(choices=VisitorEntry.ID_PROOF_CHOICES)
    id_proof_number = serializers.CharField()
    purpose = serializers.CharField()
    reference_employee_id = serializers.UUIDField()
    vehicle_number = serializers.CharField(required=False, allow_blank=True, default="")
    items_carrying = serializers.CharField(required=False, allow_blank=True, default="")
    nda_signed = serializers.BooleanField(default=False)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
