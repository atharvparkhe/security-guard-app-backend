from django.db.models import Q
from django.utils import timezone

from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from base.permissions import (
    IsGuardOrStoresManager,
    IsSecurityGuard,
    IsStoresManager,
    IsSuperAdmin,
)
from base.views import BaseAPIView
from gate.models import GateTransaction, OutwardEntry, ReturnableReturn, VisitorEntry
from gate.serializers.inward_actions import (
    InwardApproveSerializer,
    InwardConfirmInvoiceSerializer,
    InwardDraftCreateSerializer,
    InwardRejectSerializer,
    TimeOverrideSerializer,
)
from gate.serializers.outward_visitor import (
    OutwardCreateSerializer,
    ReturnableReturnCreateSerializer,
    VisitorCreateSerializer,
)
from gate.services.inward_flow import (
    process_allow_in,
    process_approve,
    process_confirm_invoice,
    process_inward_draft_create,
    process_mark_exit,
    process_reject,
    process_upload_invoice,
)
from gate.services.outward_flow import (
    process_outward_allow_in,
    process_outward_create,
    process_outward_mark_exit,
)
from gate.services.returnable_flow import (
    process_returnable_allow_in,
    process_returnable_create,
    process_returnable_mark_exit,
)
from gate.services.visitor_flow import (
    process_visitor_allow_in,
    process_visitor_create,
    process_visitor_mark_exit,
)
from gate.utils import parse_inward_list_date_filter, serialize_inward_detail
from gate.utils_outward import (
    serialize_outward_detail,
    serialize_outward_list_item,
    serialize_returnable_detail,
    serialize_transaction_detail,
    serialize_visitor_detail,
    serialize_visitor_list_item,
)
from gate.views import _entry_queryset


class InwardUploadInvoiceView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        invoice_file = request.FILES.get("invoice_image") or request.FILES.get("invoice_file")
        if not invoice_file:
            return self.error(message="invoice_image is required", status=400)
        try:
            entry = process_upload_invoice(entry, request.user, invoice_file)
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Invoice uploaded successfully",
        )


class InwardConfirmInvoiceView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        serializer = InwardConfirmInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_confirm_invoice(
                entry, request.user, serializer.validated_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Invoice confirmed successfully",
        )


class InwardAllowInView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_allow_in(entry, request.user, ser.validated_data.get("in_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        entry.refresh_from_db()
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Vehicle allowed in successfully",
        )


class InwardMarkExitView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_mark_exit(
                entry,
                request.user,
                out_time=ser.validated_data.get("out_time"),
                guard_remarks=ser.validated_data.get("guard_remarks"),
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Exit marked successfully",
        )


class InwardApproveView(BaseAPIView):
    permission_classes = [IsStoresManager]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        serializer = InwardApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_approve(entry, request.user, serializer.validated_data)
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Entry approved successfully",
        )


class InwardRejectView(BaseAPIView):
    permission_classes = [IsStoresManager]

    def post(self, request, pk):
        try:
            entry = _entry_queryset().get(pk=pk)
        except Exception:
            return self.error(message="Inward entry not found", status=404)
        serializer = InwardRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_reject(entry, request.user, serializer.validated_data)
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_inward_detail(_entry_queryset().get(pk=entry.pk), request),
            message="Entry rejected successfully",
        )


class TransactionListView(BaseAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        qs = GateTransaction.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        ).select_related("truck", "driver", "guard")
        tx_type = request.query_params.get("type")
        status = request.query_params.get("status")
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)
        if status:
            qs = qs.filter(status=status)
        data = [
            serialize_transaction_detail(gt, request) for gt in qs.order_by("-created_at")
        ]
        content = self.paginated_content(request, data, filters=filter_meta)
        return self.success(
            data={
                "filters": content["filters"],
                "pagination": content["pagination"],
                "transactions": content["results"],
            },
            message="Transactions retrieved successfully",
        )


class TransactionDetailView(BaseAPIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, pk):
        try:
            gt = GateTransaction.objects.select_related(
                "truck", "driver", "guard"
            ).get(pk=pk)
        except GateTransaction.DoesNotExist:
            return self.error(message="Transaction not found", status=404)
        return self.success(
            data=serialize_transaction_detail(gt, request),
            message="Transaction retrieved successfully",
        )


class TransactionCurrentlyInsideView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request):
        qs = (
            GateTransaction.objects.filter(
                in_time__isnull=False,
                out_time__isnull=True,
                status=GateTransaction.STATUS_INSIDE,
            )
            .select_related("truck", "driver", "guard")
            .order_by("in_time")
        )
        data = [serialize_transaction_detail(gt, request) for gt in qs]
        return self.success(
            data=self.paginated_content(request, data),
            message="Currently inside transactions retrieved",
        )


def _outward_qs():
    return OutwardEntry.objects.select_related(
        "gate_transaction__truck",
        "gate_transaction__driver",
        "guard",
    ).prefetch_related("items")


class OutwardListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsGuardOrStoresManager()]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        qs = _outward_qs().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("type")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(type=type_filter)
        today = timezone.localdate()
        stats = {
            "currently_loading": qs.filter(status=OutwardEntry.STATUS_INSIDE).count(),
            "pending_returns": OutwardEntry.objects.filter(
                status=OutwardEntry.STATUS_PENDING_RETURN
            ).count(),
            "completed_today": qs.filter(
                status=OutwardEntry.STATUS_COMPLETED,
                created_at__date=today,
            ).count(),
        }
        entries = [
            serialize_outward_list_item(e, request) for e in qs.order_by("-created_at")
        ]
        content = self.paginated_content(
            request,
            entries,
            filters=filter_meta,
            stats=stats,
        )
        return self.success(
            data={
                "filters": content["filters"],
                "stats": content["stats"],
                "pagination": content["pagination"],
                "entries": content["results"],
            },
            message="Outward entries retrieved successfully",
        )

    def post(self, request):
        merged = request.data.copy()
        merged.update(request.FILES)
        serializer = OutwardCreateSerializer(data=merged)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_outward_create(
                request.user, serializer.validated_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_outward_detail(_outward_qs().get(pk=entry.pk), request),
            message="Outward entry created successfully",
            status=201,
        )


class OutwardDetailView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request, pk):
        try:
            entry = _outward_qs().get(pk=pk)
        except OutwardEntry.DoesNotExist:
            return self.error(message="Outward entry not found", status=404)
        return self.success(
            data=serialize_outward_detail(entry, request),
            message="Outward entry retrieved successfully",
        )


class OutwardAllowInView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _outward_qs().get(pk=pk)
        except OutwardEntry.DoesNotExist:
            return self.error(message="Outward entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_outward_allow_in(entry, request.user, ser.validated_data.get("in_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_outward_detail(_outward_qs().get(pk=entry.pk), request),
            message="Outward allowed in successfully",
        )


class OutwardMarkExitView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _outward_qs().get(pk=pk)
        except OutwardEntry.DoesNotExist:
            return self.error(message="Outward entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_outward_mark_exit(entry, request.user, ser.validated_data.get("out_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_outward_detail(_outward_qs().get(pk=entry.pk), request),
            message="Outward exit marked successfully",
        )


def _returnable_qs():
    return ReturnableReturn.objects.select_related(
        "gate_transaction__truck",
        "gate_transaction__driver",
        "original_outward__gate_transaction__truck",
        "guard",
    ).prefetch_related("original_outward__items")


class ReturnableReturnListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsGuardOrStoresManager()]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        qs = _returnable_qs().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        entries = [
            serialize_returnable_detail(r, request) for r in qs.order_by("-created_at")
        ]
        content = self.paginated_content(request, entries, filters=filter_meta)
        return self.success(
            data={
                "filters": content["filters"],
                "pagination": content["pagination"],
                "entries": content["results"],
            },
            message="Returnable returns retrieved successfully",
        )

    def post(self, request):
        merged = request.data.copy()
        merged.update(request.FILES)
        serializer = ReturnableReturnCreateSerializer(data=merged)
        serializer.is_valid(raise_exception=True)
        try:
            ret = process_returnable_create(
                request.user, serializer.validated_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_returnable_detail(_returnable_qs().get(pk=ret.pk), request),
            message="Returnable return created successfully",
            status=201,
        )


class ReturnableReturnDetailView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request, pk):
        try:
            ret = _returnable_qs().get(pk=pk)
        except ReturnableReturn.DoesNotExist:
            return self.error(message="Returnable return not found", status=404)
        return self.success(
            data=serialize_returnable_detail(ret, request),
            message="Returnable return retrieved successfully",
        )


class ReturnableReturnAllowInView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            ret = _returnable_qs().get(pk=pk)
        except ReturnableReturn.DoesNotExist:
            return self.error(message="Returnable return not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_returnable_allow_in(ret, request.user, ser.validated_data.get("in_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_returnable_detail(_returnable_qs().get(pk=ret.pk), request),
            message="Return allowed in successfully",
        )


class ReturnableReturnMarkExitView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            ret = _returnable_qs().get(pk=pk)
        except ReturnableReturn.DoesNotExist:
            return self.error(message="Returnable return not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        fully = request.data.get("fully_returned", True)
        if isinstance(fully, str):
            fully = fully.lower() in ("true", "1", "yes")
        try:
            process_returnable_mark_exit(
                ret,
                request.user,
                out_time=ser.validated_data.get("out_time"),
                fully_returned=fully,
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_returnable_detail(_returnable_qs().get(pk=ret.pk), request),
            message="Return exit marked successfully",
        )


def _visitor_qs():
    return VisitorEntry.objects.select_related("reference_employee", "guard")


class VisitorListCreateView(BaseAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsSecurityGuard()]
        return [IsGuardOrStoresManager()]

    def get(self, request):
        try:
            start_date, end_date, filter_meta = parse_inward_list_date_filter(
                request.query_params
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        qs = _visitor_qs().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        today = timezone.localdate()
        stats = {
            "inside_now": VisitorEntry.objects.filter(
                status=VisitorEntry.STATUS_INSIDE
            ).count(),
            "completed_today": qs.filter(
                status=VisitorEntry.STATUS_COMPLETED,
                created_at__date=today,
            ).count(),
        }
        entries = [
            serialize_visitor_list_item(v, request) for v in qs.order_by("-created_at")
        ]
        content = self.paginated_content(
            request,
            entries,
            filters=filter_meta,
            stats=stats,
        )
        return self.success(
            data={
                "filters": content["filters"],
                "stats": content["stats"],
                "pagination": content["pagination"],
                "entries": content["results"],
            },
            message="Visitors retrieved successfully",
        )

    def post(self, request):
        merged = request.data.copy()
        merged.update(request.FILES)
        serializer = VisitorCreateSerializer(data=merged)
        serializer.is_valid(raise_exception=True)
        try:
            entry = process_visitor_create(
                request.user, serializer.validated_data, request.FILES
            )
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_visitor_detail(_visitor_qs().get(pk=entry.pk), request),
            message="Visitor entry created successfully",
            status=201,
        )


class VisitorDetailView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request, pk):
        try:
            entry = _visitor_qs().get(pk=pk)
        except VisitorEntry.DoesNotExist:
            return self.error(message="Visitor entry not found", status=404)
        return self.success(
            data=serialize_visitor_detail(entry, request),
            message="Visitor entry retrieved successfully",
        )


class VisitorAllowInView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _visitor_qs().get(pk=pk)
        except VisitorEntry.DoesNotExist:
            return self.error(message="Visitor entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_visitor_allow_in(entry, request.user, ser.validated_data.get("in_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_visitor_detail(_visitor_qs().get(pk=entry.pk), request),
            message="Visitor allowed in successfully",
        )


class VisitorMarkExitView(BaseAPIView):
    permission_classes = [IsSecurityGuard]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        try:
            entry = _visitor_qs().get(pk=pk)
        except VisitorEntry.DoesNotExist:
            return self.error(message="Visitor entry not found", status=404)
        ser = TimeOverrideSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            process_visitor_mark_exit(entry, request.user, ser.validated_data.get("out_time"))
        except ValueError as e:
            return self.error(message=str(e), status=400)
        return self.success(
            data=serialize_visitor_detail(_visitor_qs().get(pk=entry.pk), request),
            message="Visitor exit marked successfully",
        )
