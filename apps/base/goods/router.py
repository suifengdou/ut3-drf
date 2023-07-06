from rest_framework.routers import DefaultRouter
from .views import GoodsViewset, GoodsCategoryViewset, BomViewset


goods_router = DefaultRouter()
goods_router.register(r'base/goods', GoodsViewset, basename='goods')
goods_router.register(r'base/goodscategory', GoodsCategoryViewset, basename='goodscategory')
goods_router.register(r'base/bom', BomViewset, basename='bom')

