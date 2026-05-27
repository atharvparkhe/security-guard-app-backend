from rest_framework import serializers

from gate.models import Driver, Truck


def _file_url(request, field):
    if field and hasattr(field, "url"):
        return request.build_absolute_uri(field.url) if request else field.url
    return None


class TruckListSerializer(serializers.ModelSerializer):
    truck_photo = serializers.SerializerMethodField()

    class Meta:
        model = Truck
        fields = (
            "id",
            "registration_number",
            "vehicle_type",
            "owner_name",
            "owner_contact",
            "truck_photo",
        )

    def get_truck_photo(self, obj):
        request = self.context.get("request")
        return _file_url(request, obj.truck_photo)


class TruckCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = (
            "registration_number",
            "truck_photo",
            "vehicle_type",
            "owner_name",
            "owner_contact",
        )


class TruckPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Truck
        fields = ("truck_photo", "owner_name", "owner_contact", "vehicle_type")


class DriverListSerializer(serializers.ModelSerializer):
    licence_photo = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = ("id", "name", "mobile", "licence_number", "licence_photo")

    def get_licence_photo(self, obj):
        request = self.context.get("request")
        return _file_url(request, obj.licence_photo)


class DriverCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ("name", "mobile", "licence_number", "licence_photo")

    def validate_licence_number(self, value):
        if value is not None and isinstance(value, str) and not value.strip():
            return None
        return value


class DriverPatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ("name", "licence_photo", "licence_number")
