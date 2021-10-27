from rest_framework.routers import DefaultRouter
from .views import DWOCreateViewset, DWOHandleViewset, DWOCheckViewset, DWOConfirmViewset, DWOManageViewset


wodealer_router = DefaultRouter()
wodealer_router.register(r'workorder/dealers/dwocreate', DWOCreateViewset, basename='dwocreate')
wodealer_router.register(r'workorder/dealers/dwohandle', DWOHandleViewset, basename='dwohandle')
wodealer_router.register(r'workorder/dealers/dwocheck', DWOCheckViewset, basename='dwocheck')
wodealer_router.register(r'workorder/dealers/dwoconfirm', DWOConfirmViewset, basename='dwoconfirm')
wodealer_router.register(r'workorder/dealers/dwomanage', DWOManageViewset, basename='dwomanage')

