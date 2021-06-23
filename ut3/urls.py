"""ut3 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.urls import include, path
from rest_framework.documentation import include_docs_urls
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

route = DefaultRouter()

from apps.auth.groups.router import group_router
from apps.auth.users.router import users_router
from apps.base.company.router import company_router
from apps.base.department.router import department_router
from apps.base.goods.router import goods_router
from apps.base.shop.router import shop_router
from apps.utils.geography.router import geography_router
from apps.base.warehouse.router import warehouse_router
from apps.wop.woinvoice.router import woinvoice_router
from apps.sales.advancepayment.router import advance_router
from apps.sales.tailgoods.router import tailgoods_router

route.registry.extend(group_router.registry)
route.registry.extend(users_router.registry)
route.registry.extend(company_router.registry)
route.registry.extend(department_router.registry)
route.registry.extend(goods_router.registry)
route.registry.extend(shop_router.registry)
route.registry.extend(geography_router.registry)
route.registry.extend(warehouse_router.registry)
route.registry.extend(woinvoice_router.registry)
route.registry.extend(advance_router.registry)
route.registry.extend(tailgoods_router.registry)


urlpatterns = [
    url(r'^', include(route.urls)),
    url(r'^api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    url(r'^api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    url(r'^api-auth', include("rest_framework.urls")),
    url(r'^docs/', include_docs_urls("UT3接口文档")),
]
