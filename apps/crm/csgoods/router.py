from rest_framework.routers import DefaultRouter
from .views import CSGoodsViewset


csgoods_router = DefaultRouter()
csgoods_router.register(r'crm/csgoods/manage', CSGoodsViewset, basename='csgoodsmanage')



