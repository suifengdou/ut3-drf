from rest_framework.routers import DefaultRouter
from .views import OriInboundSubmitViewset, OriInboundManageViewset, InboundCheckViewset, InboundManageViewset, \
    InboundDetailValidViewset, InboundDetailManageViewset, InboundSubmitViewset, InboundValidViewset


inbound_router = DefaultRouter()
inbound_router.register(r'psi/inbound/oriinboundsubmit', OriInboundSubmitViewset, basename='oriinboundsubmit')
inbound_router.register(r'psi/inbound/oriinboundmanage', OriInboundManageViewset, basename='oriinboundmanage')
inbound_router.register(r'psi/inbound/inboundsubmit', InboundSubmitViewset, basename='inboundsubmit')
inbound_router.register(r'psi/inbound/inboundcheck', InboundCheckViewset, basename='inboundcheck')
inbound_router.register(r'psi/inbound/inboundvalid', InboundValidViewset, basename='inboundvalid')
inbound_router.register(r'psi/inbound/inboundmanage', InboundManageViewset, basename='inboundmanage')
inbound_router.register(r'psi/inbound/inbounddetailvalid', InboundDetailValidViewset, basename='inbounddetailvalid')
inbound_router.register(r'psi/inbound/inbounddetail', InboundDetailManageViewset, basename='inbounddetail')

