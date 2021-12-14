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
from apps.wop.dealers.router import wodealer_router
from apps.wop.express.router import woexpress_router
from apps.wop.storage.router import wostorage_router
from apps.wop.dealerparts.router import dealerparts_router
from apps.sales.advancepayment.router import advance_router
from apps.sales.tailgoods.router import tailgoods_router
from apps.crm.order.router import order_router
from apps.crm.customers.router import customer_router
from apps.crm.dialog.router import dialgo_router
from apps.crm.callcenter.router import callcenter_router
from apps.crm.service.router import service_router
from apps.dfc.manualorder.router import manualorder_router
from apps.dfc.batchtable.router import batchdata_router
from apps.dfc.compensation.router import compensation_router
from apps.psi.inventory.router import inventory_router
from apps.psi.outbound.router import outbound_router
from apps.psi.inbound.router import inbound_router
from apps.int.intdistributor.router import intdistributor_router
from apps.int.intaccount.router import intaccount_router
from apps.int.intreceipt.router import intreceipt_router
from apps.int.intpurchase.router import intpurchase_router
from apps.int.intstatement.router import intstatement_router


route.registry.extend(group_router.registry)
route.registry.extend(users_router.registry)
route.registry.extend(company_router.registry)
route.registry.extend(department_router.registry)
route.registry.extend(goods_router.registry)
route.registry.extend(shop_router.registry)
route.registry.extend(geography_router.registry)
route.registry.extend(warehouse_router.registry)
route.registry.extend(woinvoice_router.registry)
route.registry.extend(wodealer_router.registry)
route.registry.extend(woexpress_router.registry)
route.registry.extend(wostorage_router.registry)
route.registry.extend(dealerparts_router.registry)
route.registry.extend(advance_router.registry)
route.registry.extend(tailgoods_router.registry)
route.registry.extend(order_router.registry)
route.registry.extend(dialgo_router.registry)
route.registry.extend(callcenter_router.registry)
route.registry.extend(service_router.registry)
route.registry.extend(customer_router.registry)
route.registry.extend(manualorder_router.registry)
route.registry.extend(compensation_router.registry)
route.registry.extend(batchdata_router.registry)
route.registry.extend(inbound_router.registry)
route.registry.extend(inventory_router.registry)
route.registry.extend(outbound_router.registry)
route.registry.extend(intdistributor_router.registry)
route.registry.extend(intaccount_router.registry)
route.registry.extend(intreceipt_router.registry)
route.registry.extend(intpurchase_router.registry)
route.registry.extend(intstatement_router.registry)


urlpatterns = [
    url(r'^', include(route.urls)),
    url(r'^api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    url(r'^api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    url(r'^api-auth', include("rest_framework.urls")),
    url(r'^docs/', include_docs_urls("UT3接口文档")),
]
