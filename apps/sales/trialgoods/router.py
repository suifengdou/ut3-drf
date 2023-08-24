from rest_framework.routers import DefaultRouter
from .views import TrialOrderSubmitViewset, TrialOrderManageViewset, TrialOrderCheckViewset, TrialOrderTrackViewset,\
    TOGoodsTrackViewset, TOGoodsManage, RefundTrialOrderSubmitViewset, RefundTrialOrderManageViewset, RefundTrialOrderCheckViewset


trialgoods_router = DefaultRouter()
trialgoods_router.register(r'sales/trialgoods/trialordersubmit', TrialOrderSubmitViewset, basename='trialordersubmit')
trialgoods_router.register(r'sales/trialgoods/trialordercheck', TrialOrderCheckViewset, basename='trialordercheck')
trialgoods_router.register(r'sales/trialgoods/trialordertrack', TrialOrderTrackViewset, basename='trialordertrack')
trialgoods_router.register(r'sales/trialgoods/trialordermanage', TrialOrderManageViewset, basename='trialordermanage')
trialgoods_router.register(r'sales/trialgoods/togoodstrack', TOGoodsTrackViewset, basename='togoodstrack')
trialgoods_router.register(r'sales/trialgoods/togoodsmanage', TOGoodsManage, basename='togoodsmanage')
trialgoods_router.register(r'sales/trialgoods/refundtrialordersubmit', RefundTrialOrderSubmitViewset, basename='refundtrialordersubmit')
trialgoods_router.register(r'sales/trialgoods/refundtrialordercheck', RefundTrialOrderCheckViewset, basename='refundtrialordercheck')
trialgoods_router.register(r'sales/trialgoods/refundtrialordermanage', RefundTrialOrderManageViewset, basename='refundtrialordermanage')


