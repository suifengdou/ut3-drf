from rest_framework.routers import DefaultRouter
from .views import ServicerViewset, DialogTBViewset, DialogTBDetailViewset


dialgo_router = DefaultRouter()
dialgo_router.register(r'crm/dialog/servicer', ServicerViewset, basename='servicer')
dialgo_router.register(r'crm/dialog/dialogtb', DialogTBViewset, basename='dialogtb')
dialgo_router.register(r'crm/dialog/dialogtbdetail', DialogTBDetailViewset, basename='dialogtbdetail')



