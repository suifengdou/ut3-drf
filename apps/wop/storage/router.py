from rest_framework.routers import DefaultRouter
from .views import SWOReverseCreateViewset, SWOCreateViewset, SWOHandleViewset, SWOSupplierHandleViewset, SWOCheckViewset, \
    SWOFinanceHandleViewset, SWOManageViewset


wostorage_router = DefaultRouter()
wostorage_router.register(r'workorder/storage/sworeversecreate', SWOReverseCreateViewset, basename='sworeversecreate')
wostorage_router.register(r'workorder/storage/swocreate', SWOCreateViewset, basename='swocreate')
wostorage_router.register(r'workorder/storage/swohandle', SWOHandleViewset, basename='swohandle')
wostorage_router.register(r'baworkorder/storage/swosupplierhandle', SWOSupplierHandleViewset, basename='swosupplierhandle')
wostorage_router.register(r'workorder/storage/swocheck', SWOCheckViewset, basename='swocheck')
wostorage_router.register(r'workorder/storage/swofinancehandle', SWOFinanceHandleViewset, basename='swofinancehandle')
wostorage_router.register(r'workorder/storage/swomanage', SWOManageViewset, basename='swomanage')

