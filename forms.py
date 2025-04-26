# candidate/forms.py
from django import forms

class ResumeForm(forms.Form):
    resume = forms.FileField(
        label="Upload Resume",
        help_text="Upload your resume (PDF or DOCX)",
        widget=forms.FileInput(attrs={'accept': '.pdf,.docx'})
    )
    

