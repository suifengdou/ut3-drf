from rest_framework.routers import DefaultRouter
from .views import ShopViewset, PlatformViewset


shop_router = DefaultRouter()
shop_router.register(r'base/shop', ShopViewset, basename='shop')
shop_router.register(r'base/platform', PlatformViewset, basename='platform')

