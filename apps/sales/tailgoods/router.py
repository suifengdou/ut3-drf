from rest_framework.routers import DefaultRouter
from .views import OriTailOrderViewset, OTOGoodsViewset, TailOrderViewset, TOGoodsViewset, RefundOrderSubmitViewset, \
    RefundOrderCheckViewset, RefundOrderManageViewset, AccountInfoViewset, \
    OriTailOrderSubmitViewset, OriTailOrderCheckViewset, TailOrderCommonViewset, TailOrderSpecialViewset, \
    TailToExpenseViewset, TOGoodsCommonViewset, TOGoodsSpecialViewset, RefundToPrestoreViewset, ROGoodsReceivalViewset, \
    ROGoodsManageViewset


tailgoods_router = DefaultRouter()
tailgoods_router.register(r'sales/tailgoods/oritailordersubmit', OriTailOrderSubmitViewset, basename='oritailordersubmit')
tailgoods_router.register(r'sales/tailgoods/oritailordercheck', OriTailOrderCheckViewset, basename='oritailordercheck')
tailgoods_router.register(r'sales/tailgoods/oritailorder', OriTailOrderViewset, basename='oritailorder')
tailgoods_router.register(r'sales/tailgoods/tailtoexpense', TailToExpenseViewset, basename='tailtoexpense')
tailgoods_router.register(r'sales/tailgoods/otogoods', OTOGoodsViewset, basename='otogoods')
tailgoods_router.register(r'sales/tailgoods/tailordercommon', TailOrderCommonViewset, basename='tailordercommon')
tailgoods_router.register(r'sales/tailgoods/togoodscommon', TOGoodsCommonViewset, basename='togoodscommon')
tailgoods_router.register(r'sales/tailgoods/tailorderspecial', TailOrderSpecialViewset, basename='tailorderspecial')
tailgoods_router.register(r'sales/tailgoods/togoodsspecial', TOGoodsSpecialViewset, basename='togoodsspecial')
tailgoods_router.register(r'sales/tailgoods/tailorder', TailOrderViewset, basename='tailorder')
tailgoods_router.register(r'sales/tailgoods/togoods', TOGoodsViewset, basename='togoods')
tailgoods_router.register(r'sales/tailgoods/refundordersubmit', RefundOrderSubmitViewset, basename='refundordersubmit')
tailgoods_router.register(r'sales/tailgoods/refundordercheck', RefundOrderCheckViewset, basename='refundordercheck')
tailgoods_router.register(r'sales/tailgoods/refundordermanage', RefundOrderManageViewset, basename='refundordermanage')
tailgoods_router.register(r'sales/tailgoods/refundotoprestore', RefundToPrestoreViewset, basename='refundotoprestore')
tailgoods_router.register(r'sales/tailgoods/rogoodsreceival', ROGoodsReceivalViewset, basename='rogoodsreceival')
tailgoods_router.register(r'sales/tailgoods/rogoodsmanage', ROGoodsManageViewset, basename='rogoodsmanage')
tailgoods_router.register(r'sales/tailgoods/tgaccount', AccountInfoViewset, basename='tgaccount')

