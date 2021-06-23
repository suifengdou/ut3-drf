from rest_framework.routers import DefaultRouter
from .views import DepartmentViewset


department_router = DefaultRouter()
department_router.register(r'base/department', DepartmentViewset, basename='department')

