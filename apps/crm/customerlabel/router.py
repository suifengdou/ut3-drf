from rest_framework.routers import DefaultRouter
from .views import CustomerLabelPersonViewset, CustomerLabelFamilyViewset, CustomerLabelProductViewset, \
    CustomerLabelOrderViewset, CustomerLabelServiceViewset, CustomerLabelSatisfactionViewset, \
    CustomerLabelRefundViewset, CustomerLabelOthersViewset


customerlabel_router = DefaultRouter()
customerlabel_router.register(r'crm/customers/clperson', CustomerLabelPersonViewset, basename='clperson')
customerlabel_router.register(r'crm/customers/clfamily', CustomerLabelFamilyViewset, basename='clfamily')
customerlabel_router.register(r'crm/customers/clproduct', CustomerLabelProductViewset, basename='clproduct')
customerlabel_router.register(r'crm/customers/clorder', CustomerLabelOrderViewset, basename='clorder')
customerlabel_router.register(r'crm/customers/clservice', CustomerLabelServiceViewset, basename='clservice')
customerlabel_router.register(r'crm/customers/clsatisfaction', CustomerLabelSatisfactionViewset, basename='clsatisfaction')
customerlabel_router.register(r'crm/customers/clrefund', CustomerLabelRefundViewset, basename='clrefund')
customerlabel_router.register(r'crm/customers/clothers', CustomerLabelOthersViewset, basename='clothers')



