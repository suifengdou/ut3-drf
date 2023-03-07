from rest_framework.routers import DefaultRouter
from .views import CustomerViewset, CustomerLabelViewset


customer_router = DefaultRouter()
customer_router.register(r'crm/customers/csmanage', CustomerViewset, basename='csmanage')
customer_router.register(r'crm/customers/cslabels', CustomerLabelViewset, basename='cslabels')



