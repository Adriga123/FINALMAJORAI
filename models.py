from django.db import models

# Create your models here.
from django.conf import settings  # Import settings to access AUTH_USER_MODEL
from django.db import models

class Job(models.Model):
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=100)
    salary = models.CharField(max_length=100, blank=True, null=True)
    requirements = models.TextField()
    
    def __str__(self):
        return f"{self.title} at {self.company}"
