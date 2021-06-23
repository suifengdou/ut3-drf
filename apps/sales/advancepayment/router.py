from rest_framework.routers import DefaultRouter
from .views import AccountViewset, StatementsViewset, ExpenseViewset, VerificationPrestoreViewset, \
    VerificationExpensesViewset, ExpendListViewset, PrestoreSubmitViewset, PrestoreCheckViewset, PrestoreManageViewset, \
    MyAccountViewset


advance_router = DefaultRouter()
advance_router.register(r'sales/advance/account', AccountViewset, basename='account')
advance_router.register(r'sales/advance/myaccount', MyAccountViewset, basename='myaccount')
advance_router.register(r'sales/advance/statements', StatementsViewset, basename='statements')
advance_router.register(r'sales/advance/prestoresubmit', PrestoreSubmitViewset, basename='prestoresubmit')
advance_router.register(r'sales/advance/prestorecheck', PrestoreCheckViewset, basename='prestorecheck')
advance_router.register(r'sales/advance/prestoremanage', PrestoreManageViewset, basename='prestoremanage')
advance_router.register(r'sales/advance/expense', ExpenseViewset, basename='expense')
advance_router.register(r'sales/advance/verifyprestore', VerificationPrestoreViewset, basename='verifyprestore')
advance_router.register(r'sales/advance/verifyexpense', VerificationExpensesViewset, basename='verifyexpense')
advance_router.register(r'sales/advance/expendlist', ExpendListViewset, basename='expendlist')


