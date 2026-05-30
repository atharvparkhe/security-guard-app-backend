from django.urls import path

from orders.views import PurchaseOrderDetailView, PurchaseOrderListView

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
from gate.views_gate import (
    InwardAllowInView,
    InwardApproveView,
    InwardConfirmInvoiceView,
    InwardMarkExitView,
    InwardRejectView,
    InwardUploadInvoiceView,
    OutwardAllowInView,
    OutwardDetailView,
    OutwardListCreateView,
    OutwardMarkExitView,
    ReturnableReturnAllowInView,
    ReturnableReturnDetailView,
    ReturnableReturnListCreateView,
    ReturnableReturnMarkExitView,
    TransactionCurrentlyInsideView,
    TransactionDetailView,
    TransactionListView,
    VisitorAllowInView,
    VisitorDetailView,
    VisitorListCreateView,
    VisitorMarkExitView,
)

urlpatterns = [
    path("trucks/", TruckListCreateView.as_view(), name="truck-list-create"),
    path("trucks/<uuid:pk>/", TruckPatchView.as_view(), name="truck-patch"),
    path("drivers/", DriverListCreateView.as_view(), name="driver-list-create"),
    path("drivers/<uuid:pk>/", DriverPatchView.as_view(), name="driver-patch"),
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
        "inward/<uuid:pk>/upload-invoice/",
        InwardUploadInvoiceView.as_view(),
        name="inward-upload-invoice",
    ),
    path(
        "inward/<uuid:pk>/confirm-invoice/",
        InwardConfirmInvoiceView.as_view(),
        name="inward-confirm-invoice",
    ),
    path(
        "inward/<uuid:pk>/allow-in/",
        InwardAllowInView.as_view(),
        name="inward-allow-in",
    ),
    path(
        "inward/<uuid:pk>/mark-exit/",
        InwardMarkExitView.as_view(),
        name="inward-mark-exit",
    ),
    path(
        "inward/<uuid:pk>/approve/",
        InwardApproveView.as_view(),
        name="inward-approve",
    ),
    path(
        "inward/<uuid:pk>/reject/",
        InwardRejectView.as_view(),
        name="inward-reject",
    ),
    path(
        "inward/<uuid:pk>/decision/",
        InwardDecisionView.as_view(),
        name="inward-decision",
    ),
    path("inward/<uuid:pk>/exit/", InwardExitView.as_view(), name="inward-exit"),
    path("outward/", OutwardListCreateView.as_view(), name="outward-list-create"),
    path("outward/<uuid:pk>/", OutwardDetailView.as_view(), name="outward-detail"),
    path(
        "outward/<uuid:pk>/allow-in/",
        OutwardAllowInView.as_view(),
        name="outward-allow-in",
    ),
    path(
        "outward/<uuid:pk>/mark-exit/",
        OutwardMarkExitView.as_view(),
        name="outward-mark-exit",
    ),
    path(
        "returnable-return/",
        ReturnableReturnListCreateView.as_view(),
        name="returnable-return-list-create",
    ),
    path(
        "returnable-return/<uuid:pk>/",
        ReturnableReturnDetailView.as_view(),
        name="returnable-return-detail",
    ),
    path(
        "returnable-return/<uuid:pk>/allow-in/",
        ReturnableReturnAllowInView.as_view(),
        name="returnable-return-allow-in",
    ),
    path(
        "returnable-return/<uuid:pk>/mark-exit/",
        ReturnableReturnMarkExitView.as_view(),
        name="returnable-return-mark-exit",
    ),
    path("visitors/", VisitorListCreateView.as_view(), name="visitor-list-create"),
    path("visitors/<uuid:pk>/", VisitorDetailView.as_view(), name="visitor-detail"),
    path(
        "visitors/<uuid:pk>/allow-in/",
        VisitorAllowInView.as_view(),
        name="visitor-allow-in",
    ),
    path(
        "visitors/<uuid:pk>/mark-exit/",
        VisitorMarkExitView.as_view(),
        name="visitor-mark-exit",
    ),
    path("transactions/", TransactionListView.as_view(), name="transaction-list"),
    path(
        "transactions/currently-inside/",
        TransactionCurrentlyInsideView.as_view(),
        name="transaction-currently-inside",
    ),
    path(
        "transactions/<uuid:pk>/",
        TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    path("purchase-orders/", PurchaseOrderListView.as_view(), name="purchase-order-list"),
    path(
        "purchase-orders/<uuid:pk>/",
        PurchaseOrderDetailView.as_view(),
        name="purchase-order-detail",
    ),
    path("invoices/", InvoiceListView.as_view(), name="invoice-list"),
    path("invoices/<uuid:pk>/", InvoiceDetailView.as_view(), name="invoice-detail"),
    path("dashboard/stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
]
