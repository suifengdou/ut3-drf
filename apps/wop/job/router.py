from rest_framework.routers import DefaultRouter
from .views import JobCategoryViewset, JobOrderCreateViewset, JobOrderManageViewset, JobOrderDetailsSubmitViewset, \
    JobOrderDetailsManageViewset, InvoiceJobOrderSubmitViewset, InvoiceJobOrderManageViewset, IJOGoodsSubmitViewset, \
    IJOGoodsManageViewset



job_router = DefaultRouter()
job_router.register(r'workorder/job/jobcategory', JobCategoryViewset, basename='jobcategory')
job_router.register(r'workorder/job/jobordercreate', JobOrderCreateViewset, basename='jobordercreate')
job_router.register(r'workorder/job/jobordermanage', JobOrderManageViewset, basename='jobordermanage')
job_router.register(r'workorder/job/joborderdetailssubmit', JobOrderDetailsSubmitViewset, basename='joborderdetailssubmit')
job_router.register(r'workorder/job/joborderdetailsmanage', JobOrderDetailsManageViewset, basename='joborderdetailsmanage')
job_router.register(r'workorder/job/invoicejobordersubmit', InvoiceJobOrderSubmitViewset, basename='invoicejobordersubmit')
job_router.register(r'workorder/job/invoicejobordermanage', InvoiceJobOrderManageViewset, basename='invoicejobordermanage')
job_router.register(r'workorder/job/ijogoodssubmit', IJOGoodsSubmitViewset, basename='ijogoodssubmit')
job_router.register(r'workorder/job/ijogoodsmanage', IJOGoodsManageViewset, basename='ijogoodsmanage')

