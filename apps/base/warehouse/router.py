from rest_framework.routers import DefaultRouter
from .views import WarehouseViewset, WarehouseTypeViewset, WarehouseActivateViewset


warehouse_router = DefaultRouter()
warehouse_router.register(r'base/warehouse', WarehouseViewset, basename='warehouse')
warehouse_router.register(r'base/warehousetype', WarehouseTypeViewset, basename='warehousetype')
warehouse_router.register(r'base/warehouseactivate', WarehouseActivateViewset, basename='warehouseactivate')

