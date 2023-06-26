from rest_framework.routers import DefaultRouter
from .views import ManualOrderSubmitViewset, ManualOrderManageViewset, MOGoodsManageViewset, ManualOrderExportViewset, \
    ManualOrderExportManageViewset, MOGoodsTrackViewset, ManualOrderExportCheckViewset


manualorder_router = DefaultRouter()
manualorder_router.register(r'dfc/manualorder/mosubmit', ManualOrderSubmitViewset, basename='mosubmit')
manualorder_router.register(r'dfc/manualorder/momanage', ManualOrderManageViewset, basename='momanage')
manualorder_router.register(r'dfc/manualorder/mogoodstrack', MOGoodsTrackViewset, basename='mogoodstrack')
manualorder_router.register(r'dfc/manualorder/mogoodsmanage', MOGoodsManageViewset, basename='mogoodsmanage')
manualorder_router.register(r'dfc/manualorder/moexport', ManualOrderExportViewset, basename='moexport')
manualorder_router.register(r'dfc/manualorder/moexportcheck', ManualOrderExportCheckViewset, basename='moexportcheck')
manualorder_router.register(r'dfc/manualorder/moexportmanage', ManualOrderExportManageViewset, basename='moexportmanage')


