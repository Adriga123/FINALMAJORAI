
# HR/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
import os
import re
from docx import Document
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from .models import JobPost, Application, Notification
from .forms import JobPostForm, ResumeUploadForm
import fitz  # PyMuPDF
from django.utils import timezone
import fitz
import re
from sentence_transformers import SentenceTransformer, util
import spacy
import os
import fitz
import re
import spacy
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-mpnet-base-v2')

def extract_text_from_pdf(pdf_file):
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        text = "\n".join([page.get_text("text") for page in doc])
        return clean_text(text)
    except Exception as e:
        return str(e)

def extract_text_from_docx(docx_file):
    doc = Document(docx_file)
    return clean_text("\n".join([para.text for para in doc.paragraphs]))

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text.strip().lower()

def calculate_base_ats_score(resume_text):
    word_count = len(resume_text.split())
    length_score = min(word_count / 500 * 100, 100)
   
    sections = ['experience', 'education', 'skills', 'projects']
    section_score = sum(25 for s in sections if s in resume_text.lower())
   
    embedding = model.encode([resume_text])[0].reshape(1, -1)
    quality_score = cosine_similarity(embedding, embedding)[0][0] * 100
   
    total_score = (length_score * 0.3) + (section_score * 0.4) + (quality_score * 0.3)
    if word_count > 300:
        total_score += 10
    if 'education' in resume_text and 'experience' in resume_text:
        total_score += 15
   
    return min(total_score, 100)

def calculate_similarity(resume_text, job_desc):
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)
    job_embedding = model.encode(job_desc, convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(resume_embedding, job_embedding).item()
    return similarity * 100

def extract_keywords(text):
    doc = nlp(text.lower())
    return {token.lemma_ for token in doc if token.is_alpha and not token.is_stop}

def normalize_keyword_score(resume_text, job_desc):
    job_keywords = extract_keywords(job_desc)
    resume_keywords = extract_keywords(resume_text)
    matched_keywords = job_keywords.intersection(resume_keywords)
    if not job_keywords:
        return 0
    return (len(matched_keywords) / len(job_keywords)) * 100

def ats_score(resume_text, job_desc):
    base_score = calculate_base_ats_score(resume_text)
    cosine_score = calculate_similarity(resume_text, job_desc)
    keyword_score = normalize_keyword_score(resume_text, job_desc)
   
    combined_score = (base_score * 0.3) + (cosine_score * 0.5) + (keyword_score * 0.2)
    return round(combined_score, 2), round(base_score, 2), round(cosine_score, 2), round(keyword_score, 2)

@login_required
def hr_dashboard(request):
    job_posts = JobPost.objects.filter(user=request.user)
    applications = Application.objects.filter(job__user=request.user)
    selected_count = applications.filter(status="Selected").count()
    return render(request, 'HR/hr_dashboard.html', {
        'job_posts': job_posts,
        'applications': applications,
        'selected_count': selected_count,
    })

@login_required
def job_list(request):
    job_posts = JobPost.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'HR/job_list.html', {'job_posts': job_posts})

@login_required
def received_applications(request):
    applications = Application.objects.filter(job__user=request.user).order_by('-applied_at')
    
    if request.method == 'POST':
        for app in applications:
            new_status = request.POST.get(f'status_{app.id}')
            if new_status and new_status != app.status:
                app.status = new_status
                app.save()
                
                # Create notification for candidate
                message = (
                    f"Your application for '{app.job.job_title}' has been {new_status.lower()}."
                    if new_status == 'Selected' else
                    f"Your application for '{app.job.job_title}' was not successful."
                )
                Notification.objects.create(user=app.user, message=message)
        
        messages.success(request, "Application statuses updated successfully!")
        return redirect('received_applications')
    
    # Separate applications by status for the different sections
    selected_apps = applications.filter(status="Selected")
    pending_apps = applications.filter(status="Pending")
    rejected_apps = applications.filter(status="Rejected")
    
    context = {
        'applications': applications,
        'selected_apps': selected_apps,
        'pending_apps': pending_apps,
        'rejected_apps': rejected_apps,
    }
    return render(request, 'HR/received_applications.html', context)

@login_required
def create_job_post(request):
    if request.method == 'POST':
        form = JobPostForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.user = request.user
            job.save()
            return redirect('job_list')
    else:
        form = JobPostForm()
    return render(request, 'HR/create_job_post.html', {'form': form})

@login_required
def edit_job_post(request, job_id):
    job_post = get_object_or_404(JobPost, id=job_id, user=request.user)
    if request.method == 'POST':
        form = JobPostForm(request.POST, instance=job_post)
        if form.is_valid():
            form.save()
            return redirect('job_list')
    else:
        form = JobPostForm(instance=job_post)
    return render(request, 'HR/edit_job_post.html', {'form': form, 'job_post': job_post})

@login_required
def delete_job_post(request, job_id):
    job_post = get_object_or_404(JobPost, id=job_id, user=request.user)
    if request.method == 'POST':
        job_post.delete()
        return redirect('job_list')
    return render(request, 'HR/delete_job_post.html', {'job_post': job_post})

@login_required
def upload_resumes(request):
    if request.method == 'POST':
        form = ResumeUploadForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            job = form.cleaned_data['job']
            keywords = form.cleaned_data['keywords'] or job.keywords
            resume_files = request.FILES.getlist('resumes')
           
            for resume_file in resume_files:
                if resume_file.name.lower().endswith('.pdf'):
                    resume_text = extract_text_from_pdf(resume_file)
                elif resume_file.name.lower().endswith('.docx'):
                    resume_text = extract_text_from_docx(resume_file)
                else:
                    continue
                
                final_score, base_score, cosine_score, keyword_score = ats_score(resume_text, job.job_description)
                status = "Selected" if final_score >= 70 else "Pending"
                
                Application.objects.create(
                    user=request.user,
                    job=job,
                    resume=resume_file,
                    ats_score=final_score,
                    cosine_score=cosine_score,
                    keyword_score=keyword_score,
                    status=status
                )
            
            messages.success(request, f"Processed {len(resume_files)} resumes successfully!")
            return redirect('received_applications')
    else:
        form = ResumeUploadForm(request.user)
    return render(request, 'HR/upload_resumes.html', {'form': form})

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Application, Notification

def received_applications(request):
    if request.method == 'POST':
        # Handle status updates
        for key, value in request.POST.items():
            if key.startswith('status_'):
                app_id = key.split('_')[1]
                try:
                    application = Application.objects.get(id=app_id)
                    application.status = value
                    application.save()
                    
                    # Create notification if status changed to Selected or Rejected
                    if value in ['Selected', 'Rejected']:
                        message = (
                            f"Your application for {application.job.job_title} has been {value.lower()}."
                        )
                        Notification.objects.create(
                            user=application.user,
                            message=message
                        )
                except Application.DoesNotExist:
                    continue
        
        messages.success(request, "Application statuses updated successfully!")
        return redirect('received_applications')
    
    # GET request - show all applications
    applications = Application.objects.all().order_by('-applied_at')
    return render(request, 'HR/received_applications.html', {'applications': applications})

def notify_selected(request):
    if request.method == 'POST':
        selected_applications = Application.objects.filter(status='Selected')
        
        for application in selected_applications:
            Notification.objects.create(
                user=application.user,
                message=f"Congratulations! Your application for {application.job.job_title} has been selected."
            )
        
        messages.success(request, "Notifications sent to selected candidates")
        return redirect('received_applications')
    
    return redirect('received_applications')

def notify_rejected(request):
    if request.method == 'POST':
        rejected_applications = Application.objects.filter(status='Rejected')
        
        for application in rejected_applications:
            Notification.objects.create(
                user=application.user,
                message=f"We regret to inform you that your application for {application.job.job_title} has been rejected."
            )
        
        messages.success(request, "Notifications sent to rejected candidates")
        return redirect('received_applications')
    
    return redirect('received_applications')
def delete_application(request, app_id):
    if request.method == 'GET':
        application = get_object_or_404(Application, id=app_id)
        application.delete()
        messages.success(request, "Application deleted successfully!")
    return redirect('received_applications')

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Application, Notification

def received_applications(request):
    if request.method == 'POST':
        # Handle status updates
        for key, value in request.POST.items():
            if key.startswith('status_'):
                app_id = key.split('_')[1]
                try:
                    application = Application.objects.get(id=app_id)
                    application.status = value
                    application.save()
                    
                    # Create notification if status changed to Selected or Rejected
                    if value in ['Selected', 'Rejected']:
                        message = (
                            f"Your application for {application.job.job_title} has been {value.lower()}."
                        )
                        Notification.objects.create(
                            user=application.user,
                            message=message
                        )
                except Application.DoesNotExist:
                    continue
        
        messages.success(request, "Application statuses updated successfully!")
        return redirect('received_applications')
    
    # GET request - show all applications
    applications = Application.objects.all().order_by('-applied_at')
    return render(request, 'HR/received_applications.html', {'applications': applications})

def notify_selected(request):
    if request.method == 'POST':
        selected_applications = Application.objects.filter(status='Selected')
        
        for application in selected_applications:
            Notification.objects.create(
                user=application.user,
                message=f"Congratulations! Your application for {application.job.job_title} has been selected."
            )
        
        messages.success(request, "Notifications sent to selected candidates")
        return redirect('received_applications')
    
    return redirect('received_applications')

def notify_rejected(request):
    if request.method == 'POST':
        rejected_applications = Application.objects.filter(status='Rejected')
        
        for application in rejected_applications:
            Notification.objects.create(
                user=application.user,
                message=f"We regret to inform you that your application for {application.job.job_title} has been rejected."
            )
        
        messages.success(request, "Notifications sent to rejected candidates")
        return redirect('received_applications')
    
    return redirect('received_applications')  

def get_job_keywords(request):
    job_id = request.GET.get('job_id')
    try:
        job = JobPost.objects.get(pk=job_id, user=request.user)
        return JsonResponse({'keywords': job.keywords})
    except JobPost.DoesNotExist:
        return JsonResponse({'keywords': ''})
    
    
@login_required
def settings_page(request):
    return render(request, 'HR/settings.html')