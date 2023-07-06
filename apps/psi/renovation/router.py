from rest_framework.routers import DefaultRouter
from .views import RenovationSubmitViewset, RenovationManageViewset, RenovationGoodsManageViewset, RenovationdetailManageViewset


renovation_router = DefaultRouter()
renovation_router.register(r'psi/renovation/renovationsubmit', RenovationSubmitViewset, basename='renovationsubmit')
renovation_router.register(r'psi/renovation/renovationmanage', RenovationManageViewset, basename='renovationmanage')
renovation_router.register(r'psi/renovation/renovationgoods', RenovationGoodsManageViewset, basename='renovationgoods')
renovation_router.register(r'psi/renovation/renovationdetail', RenovationdetailManageViewset, basename='renovationdetail')


