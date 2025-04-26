# HR/forms.py
from django import forms
from .models import JobPost
from django.core.exceptions import ValidationError

class JobPostForm(forms.ModelForm):
    class Meta:
        model = JobPost
        fields = ['job_title', 'company_name', 'location', 'job_type', 'job_description', 'keywords']
        widgets = {
            'job_description': forms.Textarea(attrs={'rows': 5}),
            'keywords': forms.TextInput(attrs={'placeholder': 'e.g., Python, Django, Software Engineer'}),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class ResumeUploadForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['job'].queryset = JobPost.objects.filter(user=user)
    
    resumes = MultipleFileField(
        label='Upload Resumes',
        help_text='Upload multiple resumes (PDF or DOCX)'
    )
    
    job = forms.ModelChoiceField(
        queryset=None,
        label='Select Job',
        empty_label="Select a job",
        required=True
    )
    
    keywords = forms.CharField(
        label='Keywords',
        widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Keywords for matching (auto-filled based on job)',
        required=False
    )