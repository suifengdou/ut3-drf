from rest_framework.routers import DefaultRouter
from .views import OSWOCreateViewset, OSWOFilesViewset, SWOHandleViewset, SWOExecuteViewset, SWOPCreateViewset, \
    ServiceHandleViewset, InvoiceCreateViewset, InvoiceCheckViewset, InvoiceManageViewset, SWOManageViewset,\
    ServiceMyselfViewset, ServiceManageViewset, SWOMyselfViewset, OSWOManageViewset, OSWOHandleViewset, SWOPFilesViewset,\
    SWOCheckViewset, SWOConfirmViewset

wosatisfaction_router = DefaultRouter()
wosatisfaction_router.register(r'workorder/satisfaction/oswocreate', OSWOCreateViewset, basename='oswocreate')
wosatisfaction_router.register(r'workorder/satisfaction/oswohandle', OSWOHandleViewset, basename='oswohandle')
wosatisfaction_router.register(r'workorder/satisfaction/oswomanage', OSWOManageViewset, basename='oswomanage')
wosatisfaction_router.register(r'workorder/satisfaction/oswofiles', OSWOFilesViewset, basename='oswofiles')
wosatisfaction_router.register(r'workorder/satisfaction/swohandle', SWOHandleViewset, basename='swohandle')
wosatisfaction_router.register(r'workorder/satisfaction/swomyself', SWOMyselfViewset, basename='swomyself')
wosatisfaction_router.register(r'workorder/satisfaction/swoexecute', SWOExecuteViewset, basename='swoexecute')
wosatisfaction_router.register(r'workorder/satisfaction/swocheck', SWOCheckViewset, basename='swocheck')
wosatisfaction_router.register(r'workorder/satisfaction/swoconfirm', SWOConfirmViewset, basename='swoconfirm')
wosatisfaction_router.register(r'workorder/satisfaction/swomanage', SWOManageViewset, basename='swomanage')
wosatisfaction_router.register(r'workorder/satisfaction/swopcreate', SWOPCreateViewset, basename='swopcreate')
wosatisfaction_router.register(r'workorder/satisfaction/swopfiles', SWOPFilesViewset, basename='swopfiles')
wosatisfaction_router.register(r'workorder/satisfaction/servicemyself', ServiceMyselfViewset, basename='servicemyself')
wosatisfaction_router.register(r'workorder/satisfaction/servicehandle', ServiceHandleViewset, basename='servicehandle')
wosatisfaction_router.register(r'workorder/satisfaction/servicemanage', ServiceManageViewset, basename='servicemanage')
wosatisfaction_router.register(r'workorder/satisfaction/invoicecreate', InvoiceCreateViewset, basename='invoicecreate')
wosatisfaction_router.register(r'workorder/satisfaction/invoicecheck', InvoiceCheckViewset, basename='invoicecheck')
wosatisfaction_router.register(r'workorder/satisfaction/invoicemanage', InvoiceManageViewset, basename='invoicemanage')

