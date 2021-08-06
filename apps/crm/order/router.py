from rest_framework.routers import DefaultRouter
from .views import OriOrderSubmitViewset, OriOrderManageViewset, BMSOrderSubmitViewset


order_router = DefaultRouter()
order_router.register(r'crm/order/oriordersubmit', OriOrderSubmitViewset, basename='oriordersubmit')
order_router.register(r'crm/order/oriordermanage', OriOrderManageViewset, basename='oriordermanage')
order_router.register(r'crm/order/bmsordersubmit', BMSOrderSubmitViewset, basename='bmsordersubmit')



