from rest_framework.routers import DefaultRouter
from .views import IntDistributorMyselfViewset, IntDistributorViewset, ContactsMyselfViewset, ContactsViewset


intdistributor_router = DefaultRouter()
intdistributor_router.register(r'int/intdistributor/myselfdistributor', IntDistributorMyselfViewset, basename='myselfdistributor')
intdistributor_router.register(r'int/intdistributor/distributor', IntDistributorViewset, basename='distributor')
intdistributor_router.register(r'int/intdistributor/myselfcontacts', ContactsMyselfViewset, basename='myselfcontacts')
intdistributor_router.register(r'int/intdistributor/contacts', ContactsViewset, basename='contacts')


