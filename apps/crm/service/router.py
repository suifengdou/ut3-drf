from rest_framework.routers import DefaultRouter
from .views import OriMaintenanceSubmitViewset, OriMaintenanceBeforeViewset, OriMaintenanceWorkingViewset, \
    OriMaintenanceViewset, MaintenanceSubmitViewset, MaintenanceJudgmentViewset, MaintenanceViewset, \
    MaintenanceSummaryViewset


service_router = DefaultRouter()
service_router.register(r'crm/service/orimaintenancesubmit', OriMaintenanceSubmitViewset, basename='orimaintenancesubmit')
service_router.register(r'crm/service/orimaintenancebefore', OriMaintenanceBeforeViewset, basename='orimaintenancebefore')
service_router.register(r'crm/service/orimaintenanceworking', OriMaintenanceWorkingViewset, basename='orimaintenanceworking')
service_router.register(r'crm/service/orimaintenance', OriMaintenanceViewset, basename='orimaintenance')
service_router.register(r'crm/service/maintenancesubmit', MaintenanceSubmitViewset, basename='maintenancesubmit')
service_router.register(r'crm/service/maintenancejudgment', MaintenanceJudgmentViewset, basename='maintenancejudgment')
service_router.register(r'crm/service/maintenance', MaintenanceViewset, basename='maintenance')
service_router.register(r'crm/service/maintenancesummary', MaintenanceSummaryViewset, basename='maintenancesummary')


