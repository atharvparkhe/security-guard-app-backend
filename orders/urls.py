from django.urls import path

from orders.views import (
    PurchaseOrderDetailView,
    PurchaseOrderListView,
    VendorListCreateView,
)

urlpatterns = [
    path("orders/vendors/", VendorListCreateView.as_view(), name="vendor-list-create"),
    path(
        "orders/purchase-orders/",
        PurchaseOrderListView.as_view(),
        name="purchase-order-list",
    ),
    path(
        "orders/purchase-orders/<uuid:pk>/",
        PurchaseOrderDetailView.as_view(),
        name="purchase-order-detail",
    ),
]
