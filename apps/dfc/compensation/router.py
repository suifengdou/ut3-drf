from rest_framework.routers import DefaultRouter
from .views import CompensationSubmitViewset, CompensationViewset, BatchCompensationSubmitViewset, \
    BatchCompensationSettleViewset, BatchCompensationViewset, BCDetailSubmitViewset, BCDetailSettleViewset, \
    BCDetailViewset, CompensationCheckViewset


compensation_router = DefaultRouter()
compensation_router.register(r'dfc/compensation/compensationsubmit', CompensationSubmitViewset, basename='compensationsubmit')
compensation_router.register(r'dfc/compensation/compensationcheck', CompensationCheckViewset, basename='compensationcheck')
compensation_router.register(r'dfc/compensation/compensation', CompensationViewset, basename='compensation')
compensation_router.register(r'dfc/compensation/batchcompensationsubmit', BatchCompensationSubmitViewset, basename='batchcompensationsubmit')
compensation_router.register(r'dfc/compensation/batchcompensationsettle', BatchCompensationSettleViewset, basename='batchcompensationsettle')
compensation_router.register(r'dfc/compensation/batchcompensation', BatchCompensationViewset, basename='batchcompensation')
compensation_router.register(r'dfc/compensation/bcdetailsubmit', BCDetailSubmitViewset, basename='bcdetailsubmit')
compensation_router.register(r'dfc/compensation/bcdetailsettle', BCDetailSettleViewset, basename='bcdetailsettle')
compensation_router.register(r'dfc/compensation/bcdetail', BCDetailViewset, basename='bcdetail')


