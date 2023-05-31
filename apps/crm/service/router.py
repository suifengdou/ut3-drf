from rest_framework.routers import DefaultRouter
from .views import OriMaintenanceSubmitViewset, OriMaintenanceBeforeViewset, \
    OriMaintenanceViewset, MaintenanceSubmitViewset, MaintenanceJudgmentViewset, MaintenanceViewset, \
    MaintenanceSummaryViewset, OriMaintenanceGoodsSubmitViewset, OriMaintenanceGoodsViewset, \
    MaintenanceGoodsSubmitViewset, MaintenanceGoodsViewset, MaintenanceSignLabelViewset, MaintenancePartSummaryViewset, \
    ServiceOrderChartViewset


service_router = DefaultRouter()
service_router.register(r'crm/service/orimaintenancesubmit', OriMaintenanceSubmitViewset, basename='orimaintenancesubmit')
service_router.register(r'crm/service/orimaintenancebefore', OriMaintenanceBeforeViewset, basename='orimaintenancebefore')
service_router.register(r'crm/service/orimaintenance', OriMaintenanceViewset, basename='orimaintenance')
service_router.register(r'crm/service/maintenancesubmit', MaintenanceSubmitViewset, basename='maintenancesubmit')
service_router.register(r'crm/service/maintenancejudgment', MaintenanceJudgmentViewset, basename='maintenancejudgment')
service_router.register(r'crm/service/maintenancesignlabel', MaintenanceSignLabelViewset, basename='maintenancesignlabel')
service_router.register(r'crm/service/maintenance', MaintenanceViewset, basename='maintenance')
service_router.register(r'crm/service/maintenanceordersummary', MaintenanceSummaryViewset, basename='maintenanceordersummary')
service_router.register(r'crm/service/maintenancepartsummary', MaintenancePartSummaryViewset, basename='maintenancepartsummary')
service_router.register(r'crm/service/orimaintenancegoodssubmit', OriMaintenanceGoodsSubmitViewset, basename='orimaintenancegoodssubmit')
service_router.register(r'crm/service/orimaintenancegoods', OriMaintenanceGoodsViewset, basename='orimaintenancegoods')
service_router.register(r'crm/service/maintenancegoodssubmit', MaintenanceGoodsSubmitViewset, basename='maintenancegoodssubmit')
service_router.register(r'crm/service/maintenancegoods', MaintenanceGoodsViewset, basename='maintenancegoods')
service_router.register(r'crm/service/serviceorderchart', ServiceOrderChartViewset, basename='serviceorderchart')


