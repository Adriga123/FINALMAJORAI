# HR/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.hr_dashboard, name='hr_dashboard'),
    path('create-job-post/', views.create_job_post, name='create_job_post'),
    path('edit-job-post/<int:job_id>/', views.edit_job_post, name='edit_job_post'),
    path('delete-job-post/<int:job_id>/', views.delete_job_post, name='delete_job_post'),
    path('job-list/', views.job_list, name='job_list'),
    path('settings/', views.settings_page, name='settings'),
    path('applications/delete/<int:app_id>/', views.delete_application, name='delete_application'), 
    path('upload-resumes/', views.upload_resumes, name='upload_resumes'),
    
   
    path('applications/', views.received_applications, name='received_applications'),
    path('notify-selected/', views.notify_selected, name='notify_selected'),
    path('notify-rejected/', views.notify_rejected, name='notify_rejected'),
    path('get-job-keywords/', views.get_job_keywords, name='get_job_keywords'),
]