from rest_framework.routers import DefaultRouter
from .views import DWOSubmitViewset, DWOHandleViewset, DWOCheckViewset, DWOConfirmViewset, DWOManageViewset


wodealer_router = DefaultRouter()
wodealer_router.register(r'workorder/dealers/dwosubmit', DWOSubmitViewset, basename='dwosubmit')
wodealer_router.register(r'workorder/dealers/dwohandle', DWOHandleViewset, basename='dwohandle')
wodealer_router.register(r'workorder/dealers/dwocheck', DWOCheckViewset, basename='dwocheck')
wodealer_router.register(r'baworkorder/dealers/dwoconfirm', DWOConfirmViewset, basename='dwoconfirm')
wodealer_router.register(r'workorder/dealers/dwomanage', DWOManageViewset, basename='dwomanage')

