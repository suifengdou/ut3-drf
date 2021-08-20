from rest_framework.routers import DefaultRouter
from .views import InventoryViewset


inventory_router = DefaultRouter()
inventory_router.register(r'psi/inventory/inventorymanage', InventoryViewset, basename='inventorymanage')


