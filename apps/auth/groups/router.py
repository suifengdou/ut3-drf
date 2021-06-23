from rest_framework.routers import DefaultRouter
from .views import GroupViewset, PermissionViewset


group_router = DefaultRouter()
group_router.register(r'auth/groups', GroupViewset, basename='groups')
group_router.register(r'auth/permission', PermissionViewset, basename='permission')

