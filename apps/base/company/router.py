from rest_framework.routers import DefaultRouter
from .views import CompanyViewset


company_router = DefaultRouter()
company_router.register(r'base/company', CompanyViewset, basename='company')

