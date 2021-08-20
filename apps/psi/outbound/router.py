from rest_framework.routers import DefaultRouter
from .views import OutboundSubmitViewset


outbound_router = DefaultRouter()
outbound_router.register(r'psi/outbound/outboundsubimt', OutboundSubmitViewset, basename='outboundsubimt')


