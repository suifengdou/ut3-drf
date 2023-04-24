from rest_framework.routers import DefaultRouter
from .views import CSAddressViewset


csaddress_router = DefaultRouter()
csaddress_router.register(r'crm/csaddress/manage', CSAddressViewset, basename='csaddressmanage')



