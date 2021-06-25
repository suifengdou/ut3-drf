from rest_framework.routers import DefaultRouter
from .views import EWOReverseCreateViewset, EWOCreateViewset, EWOHandleViewset, EWOSupplierHandleViewset, EWOCheckViewset, \
    EWOFinanceHandleViewset, EWOManageViewset


woexpress_router = DefaultRouter()
woexpress_router.register(r'workorder/express/eworeversecreate', EWOReverseCreateViewset, basename='eworeversecreate')
woexpress_router.register(r'workorder/express/ewocreate', EWOCreateViewset, basename='ewocreate')
woexpress_router.register(r'workorder/express/ewohandle', EWOHandleViewset, basename='ewohandle')
woexpress_router.register(r'baworkorder/express/ewosupplierhandle', EWOSupplierHandleViewset, basename='ewosupplierhandle')
woexpress_router.register(r'workorder/express/ewocheck', EWOCheckViewset, basename='ewocheck')
woexpress_router.register(r'workorder/express/ewofinancehandle', EWOFinanceHandleViewset, basename='ewofinancehandle')
woexpress_router.register(r'workorder/express/ewomanage', EWOManageViewset, basename='ewomanage')

