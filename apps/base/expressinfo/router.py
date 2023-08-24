from rest_framework.routers import DefaultRouter
from .views import ExpressCategoryViewset, ExpressViewset


expressinfo_router = DefaultRouter()
expressinfo_router.register(r'base/express/expresscategory', ExpressCategoryViewset, basename='expresscategory')
expressinfo_router.register(r'base/express/express', ExpressViewset, basename='express')




