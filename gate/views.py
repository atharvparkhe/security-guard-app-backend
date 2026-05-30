from django.db.models import Q
from django.utils import timezone
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from base.permissions import (
    IsGuardOrStoresManager,
    IsInwardListReader,
    IsSecurityGuard,
    IsStoresManager,
    IsSuperAdmin,
)
from base.views import BaseAPIView
from gate.models import Driver, InwardEntry, Invoice, StoresAcknowledgment, Truck
from gate.serializers import (
    DriverCreateSerializer,
    DriverListSerializer,
    DriverPatchSerializer,
    InwardCreateSerializer,
    InwardExitSerializer,
    InwardUpdateSerializer,
    StoresAcknowledgmentCreateSerializer,
    StoresAcknowledgmentUpdateSerializer,
    TruckCreateSerializer,
    TruckListSerializer,
    TruckPatchSerializer,
)
from gate.services.dashboard_stats import build_dashboard_stats
from gate.services.inward_list import (
    apply_inward_status_filter,
    build_inward_list_queryset,
    build_inward_list_stats,
    serialize_inward_list_results,
)
from gate.serializers.inward_actions import InwardDraftCreateSerializer
from gate.services.inward_flow import process_inward_draft_create
from gate.services.inward_guard_flow import (
    process_exit,
    process_inward_create,
    process_inward_update,
    process_stores_acknowledgment_create,
    process_stores_acknowledgment_update,
)
from gate.utils import (
    duration_minutes,
    parse_dashboard_period_filter,
    parse_inward_list_date_filter,
    serialize_invoice,
    serialize_invoice_list_item,
    serialize_inward_detail,
    serialize_inward_list_item,
    time_inside_minutes,
)


def _entry_queryset():
    return InwardEntry.objects.select_related(
        "gate_transaction__guard",
        "truck",
        "driver",
        "invoice",
        "invoice__vendor",
        "invoice__po",
        "stores_acknowledgment__acknowledged_by",
    ).prefetch_related("lifecycle_steps", "material_items")


# --- Truck / Driver masters ---


class TruckListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsGuardOrStoresManager()]

    def get(self, request):
        qs = Truck.objects.all()
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(registration_number__icontains=search)
        data = TruckListSerializer(qs, many=True, context={"request": request}).data
        return self.success(
            data=self.paginated_content(request, data),
            message="Trucks retrieved successfully",
        )

    def post(self, request):
        serializer = TruckCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        truck = serializer.save()
        return self.success(
            data=TruckListSerializer(truck, context={"request": request}).data,
            message="Truck created successfully",
            status=201,
        )


class TruckPatchView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        try:
            truck = Truck.objects.get(pk=pk)
        except Truck.DoesNotExist:
            return self.error(message="Truck not found", status=404)
        serializer = TruckPatchSerializer(truck, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(
            data=TruckListSerializer(truck, context={"request": request}).data,
            message="Truck updated successfully",
        )


class DriverListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsGuardOrStoresManager()]

    def get(self, request):
        qs = Driver.objects.all()
        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(mobile__icontains=search)
                | Q(licence_number__icontains=search)
            )
        data = DriverListSerializer(qs, many=True, context={"request": request}).data
        return self.success(
            data=self.paginated_content(request, data),
            message="Drivers retrieved successfully",
        )

    def post(self, request):
        serializer = DriverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver = serializer.save()
        return self.success(
            data=DriverListSerializer(driver, context={"request": request}).data,
            message="Driver created successfully",
            status=201,
        )


class DriverPatchView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request, pk):
        try:
            driver = Driver.objects.get(pk=pk)
        except Driver.DoesNotExist:
            return self.error(message="Driver not found", status=404)
        serializer = DriverPatchSerializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success(
            data=DriverListSerializer(driver, context={"request": request}).data,
            message="Driver updated successfully",
        )


# --- AGENT-2: InwardListCreateView, InwardDetailUpdateView ---


class InwardListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsInwardListReader()]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        qs = build_inward_list_queryset(
            _entry_queryset(), request.user, start_date, end_date
        )
        qs = apply_inward_status_filter(
            qs, request.query_params.get("status")
        )

        stats = build_inward_list_stats(qs, request.user)
        results = serialize_inward_list_results(qs, request, request.user)
        content = self.paginated_content(
            request, results, filters=filter_meta, stats=stats
        )
        return self.success(
            data={
                "filters": content["filters"],
                "stats": content["stats"],
                "pagination": content["pagination"],
                "entries": content["results"],
            },
            message="Inward entries retrieved successfully",
        )

    def post(self, request):
        merged = request.data.copy()
        merged.update(request.FILES)

        # Legacy one-shot create when invoice_image is supplied
        if merged.get("invoice_image") or merged.get("invoice_file"):
            serializer = InwardCreateSerializer(data=merged)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            try:
                entry, gt, is_new_truck, is_new_driver = process_inward_create(
                    request.user, data, request.FILES
                )
            except ValueError as e:
                return self.error(message=str(e), status=400)
            detail = serialize_inward_detail(
                _entry_queryset().get(pk=entry.pk), request
            )
            detail["is_new_truck"] = is_new_truck
            detail["is_new_driver"] = is_new_driver
            return self.success(
                data=detail,
                message="Inward entry created successfully",
                status=201,
            )

        serializer = InwardDraftCreateSerializer(data=merged)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_inward_draft_create(
                request.user, serializer.validated_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(
                _entry_queryset().get(pk=entry.pk), request
            ),
            message="Inward draft created successfully",
            status=201,
        )


class InwardDetailUpdateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsGuardOrStoresManager()]
        return [IsSecurityGuard()]

    def get(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except InwardEntry.DoesNotExist:
            return self.error(message="Inward entry not found", status=404)
        return self.success(
            data=serialize_inward_detail(entry, request),
            message="Inward entry retrieved successfully",
        )

    def patch(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except InwardEntry.DoesNotExist:
            return self.error(message="Inward entry not found", status=404)

        merged = dict(request.data) if request.data else {}
        if request.FILES.get("invoice_image"):
            merged["invoice_image"] = request.FILES["invoice_image"]

        serializer = InwardUpdateSerializer(data=merged, partial=True)
        serializer.is_valid(raise_exception=True)
        update_data = dict(serializer.validated_data)

        invoice_fields = (
            "invoice_number",
            "invoice_from",
            "po_number",
        )
        if any(k in update_data for k in invoice_fields) or merged.get("invoice_image"):
            update_data["invoice"] = {
                k: update_data.pop(k)
                for k in list(update_data)
                if k in invoice_fields
            }

        try:
            entry = process_inward_update(
                entry, request.user, update_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        return self.success(
            data=serialize_inward_detail(
                _entry_queryset().get(pk=entry.pk), request
            ),
            message="Inward entry updated successfully",
        )


# --- AGENT-3: InwardDecisionView ---


class InwardDecisionView(BaseAPIView):
    permission_classes = [IsStoresManager]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except InwardEntry.DoesNotExist:
            return self.error(message="Inward entry not found", status=404)

        serializer = StoresAcknowledgmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            entry = process_stores_acknowledgment_create(
                entry, request.user, serializer.validated_data
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        message = (
            "Entry acknowledged successfully"
            if entry.status == InwardEntry.STATUS_GRN_GENERATED
            else "Stores acknowledgment recorded"
        )
        return self.success(
            data=serialize_inward_detail(
                _entry_queryset().get(pk=entry.pk), request
            ),
            message=message,
        )

    def patch(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except InwardEntry.DoesNotExist:
            return self.error(message="Inward entry not found", status=404)

        serializer = StoresAcknowledgmentUpdateSerializer(
            data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        try:
            entry = process_stores_acknowledgment_update(
                entry, request.user, serializer.validated_data
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        return self.success(
            data=serialize_inward_detail(
                _entry_queryset().get(pk=entry.pk), request
            ),
            message="Stores acknowledgment updated successfully",
        )


class InwardExitView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = InwardEntry.objects.select_related(
                "gate_transaction", "stores_acknowledgment"
            ).get(pk=pk)
        except InwardEntry.DoesNotExist:
            return self.error(message="Inward entry not found", status=404)

        serializer = InwardExitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            gt = process_exit(
                entry,
                request.user,
                out_time=data.get("out_time"),
                guard_remarks=data.get("guard_remarks"),
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        entry.refresh_from_db()
        return self.success(
            data={
                "entry_id": str(entry.id),
                "status": entry.status,
                "in_time": gt.in_time.isoformat() if gt.in_time else None,
                "out_time": gt.out_time.isoformat(),
                "duration_minutes": duration_minutes(gt.in_time, gt.out_time),
            },
            message="Exit marked successfully",
        )


# --- AGENT-6: InwardCurrentlyInsideView, Invoice*, Dashboard ---


class InwardCurrentlyInsideView(BaseAPIView):
    permission_classes = [IsSecurityGuard]

    def get(self, request):
        qs = (
            _entry_queryset()
            .filter(
                gate_transaction__in_time__isnull=False,
                gate_transaction__out_time__isnull=True,
            )
            .order_by("gate_transaction__in_time")
        )
        results = []
        for entry in qs:
            gt = entry.gate_transaction
            grn_number = ""
            try:
                grn_number = entry.stores_acknowledgment.grn_number
            except StoresAcknowledgment.DoesNotExist:
                grn_number = ""
            results.append(
                {
                    "id": str(entry.id),
                    "status": entry.status,
                    "is_exit_locked": entry.is_exit_locked,
                    "truck": {
                        "registration_number": entry.truck.registration_number,
                        "vehicle_type": entry.truck.vehicle_type,
                    },
                    "driver": {
                        "name": entry.driver.name,
                        "mobile": entry.driver.mobile,
                    },
                    "supplier_name": entry.invoice.supplier_name,
                    "in_time": gt.in_time.isoformat(),
                    "time_inside_minutes": time_inside_minutes(gt.in_time),
                    "grn_number": grn_number,
                }
            )
        return self.success(
            data=self.paginated_content(request, results),
            message="Currently inside trucks retrieved successfully",
        )


class InvoiceListView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        qs = (
            Invoice.objects.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date,
            )
            .select_related("vendor", "po")
            .prefetch_related("inward_entries")
            .order_by("-created_at")
        )

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(invoice_number__icontains=search)
                | Q(supplier_name__icontains=search)
                | Q(po_number__icontains=search)
            )

        vendor_id = request.query_params.get("vendor_id")
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)

        po_id = request.query_params.get("po_id")
        if po_id:
            qs = qs.filter(po_id=po_id)

        results = [serialize_invoice_list_item(inv, request) for inv in qs]
        content = self.paginated_content(request, results, filters=filter_meta)
        return self.success(
            data={
                "filters": content["filters"],
                "pagination": content["pagination"],
                "invoices": content["results"],
            },
            message="Invoices retrieved successfully",
        )


class InvoiceDetailView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request, pk):
        try:
            invoice = (
                Invoice.objects.select_related("vendor", "po")
                .prefetch_related("inward_entries")
                .get(pk=pk)
            )
        except Invoice.DoesNotExist:
            return self.error(message="Invoice not found", status=404)

        data = serialize_invoice(invoice, request)
        entry = invoice.inward_entries.order_by("-created_at").first()
        if entry:
            data["inward_entry_id"] = str(entry.id)
            data["inward_status"] = entry.status
        else:
            data["inward_entry_id"] = None
            data["inward_status"] = None

        return self.success(
            data=data,
            message="Invoice retrieved successfully",
        )


class DashboardStatsView(BaseAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            start_date, end_date, period_meta = parse_dashboard_period_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)

        content = build_dashboard_stats(start_date, end_date, period_meta)
        return self.success(
            data=content,
            message="Dashboard stats retrieved successfully",
        )
