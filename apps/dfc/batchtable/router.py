from rest_framework.routers import DefaultRouter
from .views import OriginDataSubmitViewset, OriginDataManageViewset, BatchTableSubmitViewset, BatchTableManageViewset


batchdata_router = DefaultRouter()
batchdata_router.register(r'dfc/batchdata/origindatasubmit', OriginDataSubmitViewset, basename='origindatasubmit')
batchdata_router.register(r'dfc/batchdata/origindatamanage', OriginDataManageViewset, basename='origindatamanage')
batchdata_router.register(r'dfc/batchdata/batchtablesubmit', BatchTableSubmitViewset, basename='batchtablesubmit')
batchdata_router.register(r'dfc/batchdata/batchtablemanage', BatchTableManageViewset, basename='batchtablemanage')



