from rest_framework.routers import DefaultRouter
from .views import IntStatementUnfinishedViewset


intstatement_router = DefaultRouter()
intstatement_router.register(r'int/instatement/unfinished', IntStatementUnfinishedViewset, basename='instatementunfinished')



