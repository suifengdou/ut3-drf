from rest_framework.routers import DefaultRouter
from .views import OriInvoiceSubmitViewset, OriInvoiceApplicateViewset, OriInvoiceGoodsViewset, OriInvoiceHandleViewset, \
    InvoiceHandleViewset, DeliverHandleViewset, InvoiceManageViewset, OriInvoiceManageViewset, DelivermanageViewset

woinvoice_router = DefaultRouter()
woinvoice_router.register(r'workorder/invoice/oriinvoiceapp', OriInvoiceApplicateViewset, basename='oriinvoiceapp')
woinvoice_router.register(r'workorder/invoice/oriinvoicesub', OriInvoiceSubmitViewset, basename='oriinvoicesub')
woinvoice_router.register(r'workorder/invoice/oriinvoicehand', OriInvoiceHandleViewset, basename='oriinvoicehand')
woinvoice_router.register(r'workorder/invoice/oriinvoicemanage', OriInvoiceManageViewset, basename='oriinvoicemanage')
woinvoice_router.register(r'workorder/invoice/invoicehand', InvoiceHandleViewset, basename='invoicehand')
woinvoice_router.register(r'workorder/invoice/invoicemanage', InvoiceManageViewset, basename='invoicemanage')
woinvoice_router.register(r'workorder/invoice/deliverhandle', DeliverHandleViewset, basename='deliverhandle')
woinvoice_router.register(r'workorder/invoice/delivermanage', DelivermanageViewset, basename='delivermanage')
woinvoice_router.register(r'workorder/invoice/oriinvoicegoods', OriInvoiceGoodsViewset, basename='oriinvoicegoods')
