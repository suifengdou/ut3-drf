from rest_framework.routers import DefaultRouter
from .views import SWOCreateViewset, SWOHandleViewset, SWOConfirmViewset, SWOAuditViewset, SWOManageViewset


wostorage_router = DefaultRouter()
wostorage_router.register(r'workorder/storage/swocreate', SWOCreateViewset, basename='swocreate')
wostorage_router.register(r'workorder/storage/swohandle', SWOHandleViewset, basename='swohandle')
wostorage_router.register(r'workorder/storage/swoconfirm', SWOConfirmViewset, basename='swoconfirm')
wostorage_router.register(r'workorder/storage/swoaudit', SWOAuditViewset, basename='swoaudit')
wostorage_router.register(r'workorder/storage/swomanage', SWOManageViewset, basename='swomanage')

