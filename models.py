# HR/models.py
from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone

class JobPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True)  # Added null=True for migration
    job_title = models.CharField(max_length=255)
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    job_type = models.CharField(max_length=100, choices=[
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
    ])
    job_description = models.TextField()
    keywords = models.CharField(max_length=255, help_text="Comma-separated keywords")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"

class Application(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    job = models.ForeignKey(JobPost, on_delete=models.CASCADE)
    STATUS_CHOICES = (
        ('Selected', 'Selected'),
        ('Pending', 'Pending'),
        ('Rejected', 'Rejected'),
    )
    resume = models.FileField(upload_to='applications/')
    ats_score = models.FloatField(default=0)
    cosine_score = models.FloatField(default=0)
    keyword_score = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.job.job_title}"

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
       
    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"