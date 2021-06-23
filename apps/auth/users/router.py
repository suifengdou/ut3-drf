from rest_framework.routers import DefaultRouter
from .views import UserViewset, UserPasswordViewset


users_router = DefaultRouter()
users_router.register(r'auth/users', UserViewset, basename='users')
users_router.register(r'auth/userpassword', UserPasswordViewset, basename='userpassword')

