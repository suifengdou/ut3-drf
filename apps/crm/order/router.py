from rest_framework.routers import DefaultRouter
from .views import OriOrderSubmitViewset, OriOrderManageViewset, BMSOrderSubmitViewset, OrderSubmitViewset, OrderManageViewset


order_router = DefaultRouter()
order_router.register(r'crm/order/oriordersubmit', OriOrderSubmitViewset, basename='oriordersubmit')
order_router.register(r'crm/order/oriordermanage', OriOrderManageViewset, basename='oriordermanage')
order_router.register(r'crm/order/bmsordersubmit', BMSOrderSubmitViewset, basename='bmsordersubmit')
order_router.register(r'crm/order/ordersubmit', OrderSubmitViewset, basename='ordersubmit')
order_router.register(r'crm/order/ordermanage', OrderManageViewset, basename='ordermanage')



