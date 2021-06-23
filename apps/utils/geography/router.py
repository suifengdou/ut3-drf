from rest_framework.routers import DefaultRouter
from .views import NationalityViewset, ProvinceViewset, CityViewset, DistrictViewset


geography_router = DefaultRouter()
geography_router.register(r'utils/geography/nationality', NationalityViewset, basename='nationality')
geography_router.register(r'utils/geography/province', ProvinceViewset, basename='province')
geography_router.register(r'utils/geography/city', CityViewset, basename='city')
geography_router.register(r'utils/geography/district', DistrictViewset, basename='district')

