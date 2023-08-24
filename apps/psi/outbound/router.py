from rest_framework.routers import DefaultRouter
from .views import OutboundSubmitViewset, OutboundManageViewset, OutboundDetailManageViewset


outbound_router = DefaultRouter()
outbound_router.register(r'psi/outbound/outboundsubimt', OutboundSubmitViewset, basename='outboundsubimt')
outbound_router.register(r'psi/outbound/outboundmanage', OutboundManageViewset, basename='outboundmanage')
outbound_router.register(r'psi/outbound/outbounddetail', OutboundDetailManageViewset, basename='outbounddetail')


