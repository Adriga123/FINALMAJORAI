# candidate/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('delete-notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('notification/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('apply/<int:job_id>/', views.apply_job, name='apply_job'),
    path('applied/', views.applied_jobs, name='applied_jobs'),
]