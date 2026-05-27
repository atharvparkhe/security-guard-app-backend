from base.permissions import IsGuardOrStoresManager
from base.views import BaseAPIView
from orders.models import PurchaseOrder
from orders.serializers import (
    PurchaseOrderDetailSerializer,
    PurchaseOrderListSerializer,
)


class PurchaseOrderListView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request):
        qs = PurchaseOrder.objects.select_related("vendor").order_by("-po_date")
        search = request.query_params.get("search")
        vendor = request.query_params.get("vendor")
        status = request.query_params.get("status")
        if search:
            qs = qs.filter(po_number__icontains=search)
        if vendor:
            qs = qs.filter(vendor_id=vendor)
        if status:
            qs = qs.filter(status=status)
        data = PurchaseOrderListSerializer(qs, many=True).data
        return self.success(
            data=data,
            message="Purchase orders retrieved successfully",
        )


class PurchaseOrderDetailView(BaseAPIView):
    permission_classes = [IsGuardOrStoresManager]

    def get(self, request, pk):
        try:
            po = PurchaseOrder.objects.select_related("vendor").prefetch_related(
                "items"
            ).get(pk=pk)
        except PurchaseOrder.DoesNotExist:
            return self.error(message="Purchase order not found", status=404)
        return self.success(
            data=PurchaseOrderDetailSerializer(po).data,
            message="Purchase order retrieved successfully",
        )
