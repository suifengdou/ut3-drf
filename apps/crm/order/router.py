from rest_framework.routers import DefaultRouter
from .views import OriOrderStockOutSubmitViewset, OriOrderStockOutCheckViewset, OriOrderDetailsSubmitViewset, \
    OriOrderDetailsCheckViewset, OriOrderDetailsRefundViewset, OriOrderManageViewset, DecryptOrderSubmitViewset, DecryptOrderManageViewset


order_router = DefaultRouter()
order_router.register(r'crm/order/oriorderstockoutsubmit', OriOrderStockOutSubmitViewset, basename='oriorderstockoutsubmit')
order_router.register(r'crm/order/oriorderstockoutcheck', OriOrderStockOutCheckViewset, basename='oriorderstockoutcheck')
order_router.register(r'crm/order/oriorderdetailssubmit', OriOrderDetailsSubmitViewset, basename='oriorderdetailssubmit')
order_router.register(r'crm/order/oriorderdetailscheck', OriOrderDetailsCheckViewset, basename='oriorderdetailscheck')
order_router.register(r'crm/order/oriorderdetailsrefund', OriOrderDetailsRefundViewset, basename='oriorderdetailsrefund')
order_router.register(r'crm/order/oriordermanage', OriOrderManageViewset, basename='oriordermanage')
order_router.register(r'crm/order/decryptordersubmit', DecryptOrderSubmitViewset, basename='decryptordersubmit')
order_router.register(r'crm/order/decryptordermanage', DecryptOrderManageViewset, basename='decryptordermanage')
order_router.register(r'crm/order/decryptordermanage', DecryptOrderManageViewset, basename='decryptordermanage')




