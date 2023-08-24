from rest_framework.routers import DefaultRouter
from .views import CNOrderSubmitViewset, CNOrderManageViewset

cnorder_router = DefaultRouter()
cnorder_router.register(r'fd/order/cnorder/submit', CNOrderSubmitViewset, basename='cnordersubmit')
cnorder_router.register(r'fd/order/cnorder/manage', CNOrderManageViewset, basename='cnordermanage')





