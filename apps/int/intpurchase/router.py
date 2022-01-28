from rest_framework.routers import DefaultRouter
from .views import IntPurchaseOrderSubmitViewset, IntPurchaseOrderManageViewset, IntPurchaseOrderCheckViewset, ExceptionIPOCheckViewset, ExceptionIPOManageViewset


intpurchase_router = DefaultRouter()
intpurchase_router.register(r'int/intpurchase/submit', IntPurchaseOrderSubmitViewset, basename='intpurchasesubmit')
intpurchase_router.register(r'int/intpurchase/check', IntPurchaseOrderCheckViewset, basename='intpurchasecheck')
intpurchase_router.register(r'int/intpurchase/manage', IntPurchaseOrderManageViewset, basename='intpurchasemanage')
intpurchase_router.register(r'int/exceptionipo/check', ExceptionIPOCheckViewset, basename='exceptionipocheck')
intpurchase_router.register(r'int/exceptionipo/manage', ExceptionIPOManageViewset, basename='exceptionipomanage')




