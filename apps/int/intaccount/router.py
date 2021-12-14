from rest_framework.routers import DefaultRouter
from .views import CurrencyViewset, IntAccountViewset


intaccount_router = DefaultRouter()
intaccount_router.register(r'int/intaccount/currency', CurrencyViewset, basename='currency')
intaccount_router.register(r'int/intaccount/account', IntAccountViewset, basename='account')



