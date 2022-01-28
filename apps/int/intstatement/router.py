from rest_framework.routers import DefaultRouter
from .views import IntStatementRelatedViewset, IntStatementManageViewset


intstatement_router = DefaultRouter()
intstatement_router.register(r'int/instatement/related', IntStatementRelatedViewset, basename='instatementrelated')
intstatement_router.register(r'int/instatement/manage', IntStatementManageViewset, basename='instatementmanage')



