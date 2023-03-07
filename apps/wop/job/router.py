from rest_framework.routers import DefaultRouter
from .views import JobCategoryViewset, JobOrderSubmitViewset, JobOrderManageViewset, JobOrderDetailsSubmitViewset, \
    JobOrderDetailsManageViewset, JOFilesViewset, JODFilesViewset, JobOrderDetailsAcceptViewset, \
    JobOrderDetailsPerformViewset, JobOrderDetailsTrackViewset, JobOrderTrackViewset


job_router = DefaultRouter()
job_router.register(r'workorder/job/jobcategory', JobCategoryViewset, basename='jobcategory')
job_router.register(r'workorder/job/jobordersubmit', JobOrderSubmitViewset, basename='jobordersubmit')
job_router.register(r'workorder/job/jobordertrack', JobOrderTrackViewset, basename='jobordertrack')
job_router.register(r'workorder/job/jobordermanage', JobOrderManageViewset, basename='jobordermanage')
job_router.register(r'workorder/job/joborderdetailssubmit', JobOrderDetailsSubmitViewset, basename='joborderdetailssubmit')
job_router.register(r'workorder/job/joborderdetailsaccept', JobOrderDetailsAcceptViewset, basename='joborderdetailsaccept')
job_router.register(r'workorder/job/joborderdetailsperform', JobOrderDetailsPerformViewset, basename='joborderdetailsperform')
job_router.register(r'workorder/job/joborderdetailstrack', JobOrderDetailsTrackViewset, basename='joborderdetailstrack')
job_router.register(r'workorder/job/joborderdetailsmanage', JobOrderDetailsManageViewset, basename='joborderdetailsmanage')
job_router.register(r'workorder/job/jofiles', JOFilesViewset, basename='jofiles')
job_router.register(r'workorder/job/jodfiles', JODFilesViewset, basename='jodfiles')


