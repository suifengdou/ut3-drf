from rest_framework.routers import DefaultRouter
from .views import UserViewset, UserPasswordViewset, DashboardViewset


users_router = DefaultRouter()
users_router.register(r'auth/users/users', UserViewset, basename='users')
users_router.register(r'auth/users/userpassword', UserPasswordViewset, basename='userpassword')
users_router.register(r'auth/users/dashboard', DashboardViewset, basename='dashboard')

