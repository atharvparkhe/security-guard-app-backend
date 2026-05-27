import os

from django.db import transaction
from django.utils import timezone

from core.settings import configurations
from gate.models import Driver, GateTransaction, InwardEntry, InwardEntryStatusLog, Invoice, Truck
from gate.services.inward_lifecycle import bootstrap_lifecycle_steps


def resolve_in_time(value):
    if value is None:
        return timezone.now()
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def _empty_to_none(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value


def validate_invoice_file(invoice_file):
    if not invoice_file:
        raise ValueError("invoice_image is required")
    ext = os.path.splitext(invoice_file.name)[1].lower().lstrip(".")
    if ext not in configurations.OCR_ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Allowed extensions: {', '.join(configurations.OCR_ALLOWED_EXTENSIONS)}"
        )
    max_bytes = configurations.OCR_MAX_FILE_SIZE_MB * 1024 * 1024
    if invoice_file.size > max_bytes:
        raise ValueError(f"File too large. Max {configurations.OCR_MAX_FILE_SIZE_MB} MB")


def resolve_truck(data, files=None):
    truck_id = _empty_to_none(data.get("truck_id")) or _empty_to_none(
        data.get("vehicle_id")
    )
    if truck_id:
        try:
            return Truck.objects.get(pk=truck_id), False
        except Truck.DoesNotExist as exc:
            raise ValueError("Truck not found") from exc

    reg = (data.get("registration_number") or "").strip().upper()
    if not reg:
        raise ValueError("vehicle_id or registration_number is required")

    truck = Truck.all_objects.filter(registration_number__iexact=reg).first()
    is_new = False
    if truck:
        updates = []
        if data.get("vehicle_type"):
            truck.vehicle_type = data["vehicle_type"]
            updates.append("vehicle_type")
        if data.get("owner_name") is not None:
            truck.owner_name = data.get("owner_name", "")
            updates.append("owner_name")
        if data.get("owner_contact") is not None:
            truck.owner_contact = data.get("owner_contact", "")
            updates.append("owner_contact")
        photo = (files or {}).get("truck_master_photo") or (files or {}).get(
            "truck_photo_at_entry"
        )
        if photo:
            truck.truck_photo = photo
            updates.append("truck_photo")
        if updates:
            updates.append("updated_at")
            truck.save(update_fields=updates)
    else:
        is_new = True
        master_photo = (files or {}).get("truck_master_photo") or (files or {}).get(
            "truck_photo_at_entry"
        )
        truck = Truck.objects.create(
            registration_number=reg,
            truck_photo=master_photo,
            vehicle_type=data.get("vehicle_type", Truck.VEHICLE_TYPE_TRUCK),
            owner_name=data.get("owner_name", data.get("truck_owner_name", "")),
            owner_contact=data.get("owner_contact", ""),
        )
    return truck, is_new


def resolve_driver(data, files=None):
    driver_id = _empty_to_none(data.get("driver_id"))
    if driver_id:
        try:
            return Driver.objects.get(pk=driver_id), False
        except Driver.DoesNotExist as exc:
            raise ValueError("Driver not found") from exc

    mobile = (data.get("driver_mobile") or data.get("mobile") or "").strip()
    name = (data.get("driver_name") or data.get("name") or "").strip()
    if not mobile or not name:
        raise ValueError("driver_id or driver name and mobile are required")

    driver = Driver.all_objects.filter(mobile=mobile).first()
    is_new = False
    licence_photo = (files or {}).get("driver_licence_photo")
    licence_number = (
        data.get("driver_licence_number") or data.get("licence_number") or ""
    ).strip()

    if driver:
        driver.name = name
        if licence_photo:
            driver.licence_photo = licence_photo
        if licence_number and licence_number != (driver.licence_number or ""):
            driver.licence_number = licence_number
        driver.save()
    else:
        is_new = True
        driver = Driver.objects.create(
            name=name,
            mobile=mobile,
            licence_number=licence_number or None,
            licence_photo=licence_photo,
        )
    return driver, is_new


def create_invoice(invoice_data, invoice_file=None):
    if invoice_file:
        validate_invoice_file(invoice_file)

    supplier_name = (
        invoice_data.get("invoice_from")
        or invoice_data.get("supplier_name")
        or ""
    ).strip()

    return Invoice.objects.create(
        supplier_name=supplier_name,
        invoice_number=(invoice_data.get("invoice_number") or "").strip(),
        po_number=(invoice_data.get("po_number") or "").strip(),
        invoice_file=invoice_file,
    )


def replace_invoice_header(invoice, invoice_data, invoice_file=None):
    if invoice_file:
        validate_invoice_file(invoice_file)
        invoice.invoice_file = invoice_file

    if "invoice_from" in invoice_data or "supplier_name" in invoice_data:
        invoice.supplier_name = (
            invoice_data.get("invoice_from")
            or invoice_data.get("supplier_name")
            or invoice.supplier_name
        ).strip()
    if "invoice_number" in invoice_data:
        invoice.invoice_number = (invoice_data.get("invoice_number") or "").strip()
    if "po_number" in invoice_data:
        invoice.po_number = (invoice_data.get("po_number") or "").strip()

    invoice.save()
    return invoice


def process_inward_create(user, data, files):
    truck, is_new_truck = resolve_truck(data, files)
    driver, is_new_driver = resolve_driver(data, files)

    invoice_payload = data.get("invoice") or data
    invoice_file = (files or {}).get("invoice_image") or (files or {}).get(
        "invoice_file"
    )

    entry_in_time = resolve_in_time(data.get("in_time"))

    with transaction.atomic():
        invoice = create_invoice(invoice_payload, invoice_file=invoice_file)
        gt = GateTransaction.objects.create(
            truck=truck,
            driver=driver,
            truck_photo_at_entry=(files or {}).get("truck_photo_at_entry"),
            number_of_passengers=data.get("number_of_passengers", 0),
            in_time=entry_in_time,
            transaction_type=GateTransaction.TRANSACTION_INWARD,
            guard=user,
        )
        entry = InwardEntry.objects.create(
            gate_transaction=gt,
            truck=truck,
            driver=driver,
            invoice=invoice,
            status=InwardEntry.STATUS_PENDING_VERIFICATION,
            guard_remarks=data.get("guard_remarks", ""),
        )
        InwardEntryStatusLog.objects.create(
            inward_entry=entry,
            from_status="",
            to_status=InwardEntry.STATUS_PENDING_VERIFICATION,
            changed_by=user,
            notes="Inward created",
        )
        bootstrap_lifecycle_steps(entry, user=user)

    return entry, gt, is_new_truck, is_new_driver


def process_inward_update(entry, user, data, files):
    if entry.status != InwardEntry.STATUS_PENDING_VERIFICATION:
        raise ValueError(f"Cannot update inward in status '{entry.status}'")
    if entry.gate_transaction.guard_id != user.id:
        raise ValueError("You are not the guard who created this entry.")

    truck = entry.truck
    driver = entry.driver

    if (
        data.get("truck_id")
        or data.get("vehicle_id")
        or data.get("registration_number")
    ):
        truck, _ = resolve_truck(data, files)
    if data.get("driver_id") or data.get("driver_mobile") or data.get("mobile"):
        driver, _ = resolve_driver(data, files)

    gt = entry.gate_transaction
    gt.truck = truck
    gt.driver = driver
    if "number_of_passengers" in data:
        gt.number_of_passengers = data["number_of_passengers"]
    if (files or {}).get("truck_photo_at_entry"):
        gt.truck_photo_at_entry = files["truck_photo_at_entry"]
    if data.get("in_time") is not None:
        gt.in_time = resolve_in_time(data.get("in_time"))
    gt.save()

    entry.truck = truck
    entry.driver = driver
    if data.get("guard_remarks") is not None:
        entry.guard_remarks = data["guard_remarks"]

    invoice_payload = data.get("invoice")
    if invoice_payload is not None:
        invoice_file = (files or {}).get("invoice_image") or (files or {}).get(
            "invoice_file"
        )
        replace_invoice_header(entry.invoice, invoice_payload, invoice_file=invoice_file)

    entry.save()
    bootstrap_lifecycle_steps(entry, user=user)
    return entry
