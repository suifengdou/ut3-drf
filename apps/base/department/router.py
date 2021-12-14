from rest_framework.routers import DefaultRouter
from .views import DepartmentViewset, CenterViewset


department_router = DefaultRouter()
department_router.register(r'base/department', DepartmentViewset, basename='department')
department_router.register(r'base/center', CenterViewset, basename='center')

