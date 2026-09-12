from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tracker.views import AdminSchoolExportView, AdminSchoolsView, NotificationViewSet, PointTemplateViewSet, EntryViewSet, RunReminderCheckView, VerifySubmissionView, AdminSchoolDetailView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from tracker.views import upload_photo
from tracker.views import MeView
from tracker.views import RegisterView
from tracker.views import MonthStatusView
from tracker.views import SubmitMonthView
from tracker.views import ConsolidatedExportView




router = DefaultRouter()
router.register('points', PointTemplateViewSet, basename='point')
router.register('entries', EntryViewSet, basename='entry')
router.register('notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/upload-photo/', upload_photo, name='upload-photo'),
    path('api/me/', MeView.as_view(), name='me'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/month-status/', MonthStatusView.as_view(), name='month-status'),
    path('api/submit-month/', SubmitMonthView.as_view(), name='submit-month'),
    path('api/admin/schools/', AdminSchoolsView.as_view(), name='admin-schools'),
    path('api/admin/schools/<int:school_id>/', AdminSchoolDetailView.as_view(), name='admin-school-detail'),
    path('api/admin/schools/<int:school_id>/verify/', VerifySubmissionView.as_view(), name='verify-submission'),
    path('api/admin/schools/<int:school_id>/export/', AdminSchoolExportView.as_view(), name='admin-school-export'),
    path('api/run-reminder-check/', RunReminderCheckView.as_view(), name='run-reminder-check'),
    path('api/admin/consolidated-export/', ConsolidatedExportView.as_view(), name='consolidated-export'),

]