from rest_framework.routers import DefaultRouter
from .views import LogisticsViewset, DepponReceptionViewset


logistics_router = DefaultRouter()
logistics_router.register(r'psi/logistics/logisticsorder', LogisticsViewset, basename='logisticsorder')
logistics_router.register(r'psi/logistics/deppon/reception', DepponReceptionViewset, basename='depponreception')


