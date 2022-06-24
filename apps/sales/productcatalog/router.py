from rest_framework.routers import DefaultRouter
from .views import ProductCatalogMyselfViewset, ProductCatalogManageViewset


product_catalog_router = DefaultRouter()
product_catalog_router.register(r'sales/productcatalog/myproductcatalog', ProductCatalogMyselfViewset, basename='myproductcatalog')
product_catalog_router.register(r'sales/productcatalog/productcatalogmanage', ProductCatalogManageViewset, basename='productcatalogmanage')


