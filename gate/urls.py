from django.urls import path

from gate.views import (
    DashboardStatsView,
    DriverListCreateView,
    DriverPatchView,
    InvoiceDetailView,
    InvoiceListView,
    InwardCurrentlyInsideView,
    InwardDecisionView,
    InwardDetailUpdateView,
    InwardExitView,
    InwardListCreateView,
    TruckListCreateView,
    TruckPatchView,
)
from orders.views import PurchaseOrderDetailView, PurchaseOrderListView

urlpatterns = [
    path("trucks/", TruckListCreateView.as_view(), name="truck-list-create"),
    path("trucks/<uuid:pk>/", TruckPatchView.as_view(), name="truck-patch"),
    path("drivers/", DriverListCreateView.as_view(), name="driver-list-create"),
    path("drivers/<uuid:pk>/", DriverPatchView.as_view(), name="driver-patch"),
    path("purchase-orders/", PurchaseOrderListView.as_view(), name="purchase-order-list"),
    path(
        "purchase-orders/<uuid:pk>/",
        PurchaseOrderDetailView.as_view(),
        name="purchase-order-detail",
    ),
    path("inward/", InwardListCreateView.as_view(), name="inward-list-create"),
    path(
        "inward/currently-inside/",
        InwardCurrentlyInsideView.as_view(),
        name="inward-currently-inside",
    ),
    path(
        "inward/<uuid:pk>/",
        InwardDetailUpdateView.as_view(),
        name="inward-detail-update",
    ),
    path(
        "inward/<uuid:pk>/decision/",
        InwardDecisionView.as_view(),
        name="inward-decision",
    ),
    path("inward/<uuid:pk>/exit/", InwardExitView.as_view(), name="inward-exit"),
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<uuid:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
