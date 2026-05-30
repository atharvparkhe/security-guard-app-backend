from django.utils import timezone

from gate.utils import duration_minutes, file_url, time_inside_minutes


def serialize_outward_item(item):
    return {
        "id": str(item.id),
        "description": item.description,
        "quantity": item.quantity,
        "unit": item.unit,
        "remarks": item.remarks,
    }


def serialize_outward_detail(entry, request):
    gt = entry.gate_transaction
    return {
        "id": str(entry.id),
        "type": entry.type,
        "status": entry.status,
        "document_number": entry.document_number,
        "party_name": entry.party_name,
        "expected_return_date": (
            entry.expected_return_date.isoformat()
            if entry.expected_return_date
            else None
        ),
        "document_photo": file_url(request, entry.document_photo),
        "guard_remarks": entry.guard_remarks,
        "items": [serialize_outward_item(i) for i in entry.items.all()],
        "gate_transaction": {
            "id": str(gt.id),
            "in_time": gt.in_time.isoformat() if gt.in_time else None,
            "out_time": gt.out_time.isoformat() if gt.out_time else None,
            "status": gt.status,
            "truck": {
                "id": str(gt.truck_id),
                "registration_number": gt.truck.registration_number,
            },
            "driver": {
                "id": str(gt.driver_id),
                "name": gt.driver.name,
                "mobile": gt.driver.mobile,
            },
        },
        "created_at": entry.created_at.isoformat(),
    }


def serialize_outward_list_item(entry, request):
    gt = entry.gate_transaction
    return {
        "id": str(entry.id),
        "type": entry.type,
        "status": entry.status,
        "document_number": entry.document_number,
        "party_name": entry.party_name,
        "registration_number": gt.truck.registration_number,
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "out_time": gt.out_time.isoformat() if gt.out_time else None,
        "time_inside_minutes": time_inside_minutes(gt.in_time),
        "expected_return_date": (
            entry.expected_return_date.isoformat()
            if entry.expected_return_date
            else None
        ),
        "created_at": entry.created_at.isoformat(),
    }


def serialize_returnable_detail(ret, request):
    return {
        "id": str(ret.id),
        "status": ret.status,
        "condition": ret.condition,
        "quantity_returned": ret.quantity_returned,
        "remarks": ret.remarks,
        "original_outward": serialize_outward_detail(ret.original_outward, request),
        "gate_transaction": {
            "id": str(ret.gate_transaction_id),
            "in_time": (
                ret.gate_transaction.in_time.isoformat()
                if ret.gate_transaction.in_time
                else None
            ),
            "out_time": (
                ret.gate_transaction.out_time.isoformat()
                if ret.gate_transaction.out_time
                else None
            ),
        },
        "created_at": ret.created_at.isoformat(),
    }


def serialize_visitor_detail(entry, request):
    return {
        "id": str(entry.id),
        "visitor_name": entry.visitor_name,
        "company": entry.company,
        "phone": entry.phone,
        "id_proof_type": entry.id_proof_type,
        "id_proof_number": entry.id_proof_number,
        "id_proof_photo": file_url(request, entry.id_proof_photo),
        "purpose": entry.purpose,
        "reference_employee": {
            "id": str(entry.reference_employee_id),
            "full_name": entry.reference_employee.get_full_name()
            or entry.reference_employee.username,
        },
        "vehicle_number": entry.vehicle_number,
        "items_carrying": entry.items_carrying,
        "nda_signed": entry.nda_signed,
        "nda_photo": file_url(request, entry.nda_photo),
        "in_time": entry.in_time.isoformat() if entry.in_time else None,
        "out_time": entry.out_time.isoformat() if entry.out_time else None,
        "duration_minutes": duration_minutes(entry.in_time, entry.out_time),
        "status": entry.status,
        "remarks": entry.remarks,
        "created_at": entry.created_at.isoformat(),
    }


def serialize_visitor_list_item(entry, request):
    return {
        "id": str(entry.id),
        "visitor_name": entry.visitor_name,
        "company": entry.company,
        "purpose": entry.purpose,
        "reference_employee_name": entry.reference_employee.get_full_name()
        or entry.reference_employee.username,
        "nda_signed": entry.nda_signed,
        "status": entry.status,
        "in_time": entry.in_time.isoformat() if entry.in_time else None,
        "out_time": entry.out_time.isoformat() if entry.out_time else None,
        "time_inside_minutes": time_inside_minutes(entry.in_time),
        "created_at": entry.created_at.isoformat(),
    }


def serialize_transaction_detail(gt, request):
    return {
        "id": str(gt.id),
        "transaction_type": gt.transaction_type,
        "status": gt.status,
        "in_time": gt.in_time.isoformat() if gt.in_time else None,
        "out_time": gt.out_time.isoformat() if gt.out_time else None,
        "truck": {
            "id": str(gt.truck_id),
            "registration_number": gt.truck.registration_number,
        },
        "driver": {
            "id": str(gt.driver_id),
            "name": gt.driver.name,
            "mobile": gt.driver.mobile,
        },
        "guard": {
            "id": str(gt.guard_id),
            "full_name": gt.guard.get_full_name() or gt.guard.username,
        },
        "remarks": gt.remarks,
        "created_at": gt.created_at.isoformat(),
    }
