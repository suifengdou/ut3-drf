from rest_framework.routers import DefaultRouter
from .views import OriCallLogViewset, OriCallLogSubmitViewset, OriCallLogCheckViewset, CallLogViewset


callcenter_router = DefaultRouter()
callcenter_router.register(r'crm/callcenter/oricalllogsubmit', OriCallLogSubmitViewset, basename='oricalllogsubmit')
callcenter_router.register(r'crm/callcenter/oricalllogcheck', OriCallLogCheckViewset, basename='oricalllogcheck')
callcenter_router.register(r'crm/callcenter/oricalllog', OriCallLogViewset, basename='oricalllog')
callcenter_router.register(r'crm/callcenter/calllog', CallLogViewset, basename='calllog')



