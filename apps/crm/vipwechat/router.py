from rest_framework.routers import DefaultRouter
from .views import SpecialistViewset, VIPWechatMyselfViewset, VIPWechatManageViewset


vipwechat_router = DefaultRouter()
vipwechat_router.register(r'crm/vipwechat/specialist', SpecialistViewset, basename='specialist')
vipwechat_router.register(r'crm/vipwechat/vipwmyself', VIPWechatMyselfViewset, basename='vipwmyself')
vipwechat_router.register(r'crm/vipwechat/vipwmanage', VIPWechatManageViewset, basename='vipwmanage')



