from rest_framework.routers import DefaultRouter
from .views import LabelCategoryViewset, LabelViewset, LabelCustomerOrderSubmitViewset, \
    LabelCustomerOrderViewset, LabelCustomerViewset, \
    LabelCustomerOrderDetailsSubmitViewset, LabelCustomerOrderDetailsViewset, LabelCustomerCenterViewset


label_router = DefaultRouter()
label_router.register(r'crm/label/labelcategory', LabelCategoryViewset, basename='labelcategory')
label_router.register(r'crm/label/label', LabelViewset, basename='label')
label_router.register(r'crm/label/labelcustomerordersubmit', LabelCustomerOrderSubmitViewset, basename='labelcustomerordersubmit')
label_router.register(r'crm/label/labelcustomerorder', LabelCustomerOrderViewset, basename='labelcustomerorder')
label_router.register(r'crm/label/labelcustomerorderdetailssubmit', LabelCustomerOrderDetailsSubmitViewset, basename='labelcustomerorderdetailssubmit')
label_router.register(r'crm/label/labelcustomerorderdetails', LabelCustomerOrderDetailsViewset, basename='labelcustomerorderdetails')
label_router.register(r'crm/label/labelcustomercenter', LabelCustomerCenterViewset, basename='labelcustomercenter')
label_router.register(r'crm/label/labelcustomer', LabelCustomerViewset, basename='labelcustomer')



