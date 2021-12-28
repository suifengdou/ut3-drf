from rest_framework.routers import DefaultRouter
from .views import IntReceiptCreateViewset, IntReceiptSubmitViewset, IntReceiptCheckViewset, IntReceiptManageViewset, \
    IntReceiptExecuteViewset, IntReceiptBalanceViewset


intreceipt_router = DefaultRouter()
intreceipt_router.register(r'int/intreceipt/create', IntReceiptCreateViewset, basename='intreceiptcreate')
intreceipt_router.register(r'int/intreceipt/submit', IntReceiptSubmitViewset, basename='intreceiptsubmit')
intreceipt_router.register(r'int/intreceipt/check', IntReceiptCheckViewset, basename='intreceiptcheck')
intreceipt_router.register(r'int/intreceipt/execute', IntReceiptExecuteViewset, basename='intreceiptexecute')
intreceipt_router.register(r'int/intreceipt/balance', IntReceiptBalanceViewset, basename='intreceiptbalance')
intreceipt_router.register(r'int/intreceipt/manage', IntReceiptManageViewset, basename='intreceiptmanage')



