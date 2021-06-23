from rest_framework.routers import DefaultRouter
from .views import GoodsViewset, GoodsCategoryViewset


goods_router = DefaultRouter()
goods_router.register(r'base/goods', GoodsViewset, basename='goods')
goods_router.register(r'base/goodscategory', GoodsCategoryViewset, basename='goodscategory')

