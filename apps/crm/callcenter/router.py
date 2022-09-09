from rest_framework.routers import DefaultRouter
from .views import OriCallLogViewset, OriCallLogSubmitViewset, OriCallLogCheckViewset, CallLogViewset, CallLogHandleViewset, CallLogExecuteViewset, CallLogCheckViewset


callcenter_router = DefaultRouter()
callcenter_router.register(r'crm/callcenter/oricalllogsubmit', OriCallLogSubmitViewset, basename='oricalllogsubmit')
callcenter_router.register(r'crm/callcenter/oricalllogcheck', OriCallLogCheckViewset, basename='oricalllogcheck')
callcenter_router.register(r'crm/callcenter/oricalllog', OriCallLogViewset, basename='oricalllog')
callcenter_router.register(r'crm/callcenter/callloghandle', CallLogHandleViewset, basename='callloghandle')
callcenter_router.register(r'crm/callcenter/calllogexecute', CallLogExecuteViewset, basename='calllogexecute')
callcenter_router.register(r'crm/callcenter/calllogcheck', CallLogCheckViewset, basename='calllogcheck')
callcenter_router.register(r'crm/callcenter/calllog', CallLogViewset, basename='calllog')



