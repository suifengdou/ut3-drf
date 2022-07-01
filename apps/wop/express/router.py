from rest_framework.routers import DefaultRouter
from .views import EWOCreateViewset, EWOHandleViewset, EWOExecuteViewset, EWOCheckViewset, \
    EWOFinanceHandleViewset, EWOManageViewset, EWOPhotoViewset


woexpress_router = DefaultRouter()
woexpress_router.register(r'workorder/express/ewocreate', EWOCreateViewset, basename='ewocreate')
woexpress_router.register(r'workorder/express/ewohandle', EWOHandleViewset, basename='ewohandle')
woexpress_router.register(r'workorder/express/ewoexecute', EWOExecuteViewset, basename='ewoexecute')
woexpress_router.register(r'workorder/express/ewocheck', EWOCheckViewset, basename='ewocheck')
woexpress_router.register(r'workorder/express/ewofinancehandle', EWOFinanceHandleViewset, basename='ewofinancehandle')
woexpress_router.register(r'workorder/express/ewomanage', EWOManageViewset, basename='ewomanage')
woexpress_router.register(r'workorder/express/ewophoto', EWOPhotoViewset, basename='ewophoto')

