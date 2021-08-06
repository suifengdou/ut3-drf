from rest_framework.routers import DefaultRouter
from .views import OriTailOrderViewset, OTOGoodsViewset, TailOrderViewset, TOGoodsViewset, RefundOrderSubmitViewset, \
    RefundOrderCheckViewset, RefundOrderManageViewset, AccountInfoViewset, TailPartsOrderViewset, \
    OriTailOrderSubmitViewset, OriTailOrderCheckViewset, TailOrderCommonViewset, TailOrderSpecialViewset, \
    TailToExpenseViewset, TOGoodsCommonViewset, TOGoodsSpecialViewset, RefundToPrestoreViewset, ROGoodsReceivalViewset, \
    ROGoodsManageViewset


tailgoods_router = DefaultRouter()
tailgoods_router.register(r'sales/tailgoods/oritailordersubmit', OriTailOrderSubmitViewset, basename='oritailordersubmit')


