from rest_framework.routers import DefaultRouter
from .views import ServicerViewset, DialogTBViewset, DialogTBDetailViewset, DialogTBDetailSubmitViewset, \
    DialogTBDetailSubmitMyselfViewset, DialogTBWordsViewset, DialogJDViewset, DialogJDDetailSubmitViewset, \
    DialogJDDetailViewset, DialogJDWordsViewset, DialogOWViewset, DialogOWDetailSubmitViewset, DialogOWDetailViewset, \
    DialogOWWordsViewset, DialogOWViewsetSubmit


dialgo_router = DefaultRouter()
dialgo_router.register(r'crm/dialog/servicer', ServicerViewset, basename='servicer')
dialgo_router.register(r'crm/dialog/dialogtb', DialogTBViewset, basename='dialogtb')
dialgo_router.register(r'crm/dialog/dialogtbdetailmyself', DialogTBDetailSubmitMyselfViewset, basename='dialogtbdetailmyself')
dialgo_router.register(r'crm/dialog/dialogtbdetailsubmit', DialogTBDetailSubmitViewset, basename='dialogtbdetailsubmit')
dialgo_router.register(r'crm/dialog/dialogtbdetail', DialogTBDetailViewset, basename='dialogtbdetail')
dialgo_router.register(r'crm/dialog/dialogtbwords', DialogTBWordsViewset, basename='dialogtbwords')
dialgo_router.register(r'crm/dialog/dialogjd', DialogJDViewset, basename='dialogjd')
dialgo_router.register(r'crm/dialog/dialogjddetailsubmit', DialogJDDetailSubmitViewset, basename='dialogjddetailsubmit')
dialgo_router.register(r'crm/dialog/dialogjddetail', DialogJDDetailViewset, basename='dialogjddetail')
dialgo_router.register(r'crm/dialog/dialogjdbwords', DialogJDWordsViewset, basename='dialogjdbwords')
dialgo_router.register(r'crm/dialog/dialogow', DialogOWViewset, basename='dialogow')
dialgo_router.register(r'crm/dialog/dialogowsubmit', DialogOWViewset, basename='dialogowsubmit')
dialgo_router.register(r'crm/dialog/dialogowdetailsubmit', DialogOWDetailSubmitViewset, basename='dialogowdetailsubmit')
dialgo_router.register(r'crm/dialog/dialogowdetail', DialogOWDetailViewset, basename='dialogowdetail')
dialgo_router.register(r'crm/dialog/dialogowwords', DialogOWWordsViewset, basename='dialogowwords')



