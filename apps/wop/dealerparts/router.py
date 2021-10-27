from rest_framework.routers import DefaultRouter
from .views import DealerPartsCreateViewset, DealerPartsSubmitViewset, DealerPartsManageViewset


dealerparts_router = DefaultRouter()
dealerparts_router.register(r'workorder/dealerparts/dpcreate', DealerPartsCreateViewset, basename='dpcreate')
dealerparts_router.register(r'workorder/dealerparts/dpsubmit', DealerPartsSubmitViewset, basename='dpsubmit')
dealerparts_router.register(r'workorder/dealerparts/dpmanage', DealerPartsManageViewset, basename='dpmanage')



