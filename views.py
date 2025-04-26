# candidate/views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
  
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from candidate.forms import ResumeForm
from HR.models import JobPost, Application, Notification  # Import Notification model
from django.contrib import messages  # Import messages for feedback
import fitz
import re
from sentence_transformers import SentenceTransformer, util
import spacy
import os
import fitz
import re
import spacy
from django.conf import settings
from sentence_transformers import SentenceTransformer, util
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
from PyPDF2 import PdfReader
import numpy as np
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from candidate.forms import ResumeForm
from HR.models import JobPost, Application, Notification
from django.contrib import messages
import fitz
import re
from sentence_transformers import SentenceTransformer, util
import spacy
from docx import Document
from django.views.decorators.http import require_POST
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
def delete_notification(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted successfully.")
    return redirect('candidate_dashboard')

@login_required
def candidate_dashboard(request):
    jobs = JobPost.objects.all()
    search_query = request.GET.get('search', '')
    location_filter = request.GET.get('location', '')
    category_filter = request.GET.get('category', '')
    
    if search_query:
        jobs = jobs.filter(job_title__icontains=search_query)
    if location_filter:
        jobs = jobs.filter(location__icontains=location_filter)
    if category_filter:
        jobs = jobs.filter(job_description__icontains=category_filter) | jobs.filter(keywords__icontains=category_filter)

    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = notifications.filter(is_read=False).count()

    context = {
        'jobs': jobs,
        'search_query': search_query,
        'location_filter': location_filter,
        'category_filter': category_filter,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'candidate/candidate_dashboard.html', context)

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})
@login_required
def browse_jobs(request):
    jobs = JobPost.objects.all()
    return render(request, 'candidate/browse_jobs.html', {'jobs': jobs})

@login_required
def apply_job(request, job_id):
    job = get_object_or_404(JobPost, id=job_id)
    if request.method == 'POST':
        form = ResumeForm(request.POST, request.FILES)
        if form.is_valid():
            resume_file = request.FILES['resume']
            
            # Check file extension
            if resume_file.name.endswith('.pdf'):
                resume_text = extract_text_from_pdf(resume_file)
            elif resume_file.name.endswith('.docx'):
                resume_text = extract_text_from_docx(resume_file)
            else:
                messages.error(request, "Please upload a PDF or DOCX file.")
                return redirect('apply_job', job_id=job_id)
            
            final_score, base_score, cosine_score, keyword_score = ats_score(resume_text, job.job_description)
            status = "Selected" if final_score >= 70 else "Pending"
            
            # Create application
            application = Application.objects.create(
                user=request.user,
                job=job,
                resume=resume_file,
                ats_score=final_score,
                cosine_score=cosine_score,
                keyword_score=keyword_score,
                status=status
            )
            
            # Create notification for HR
            Notification.objects.create(
                user=job.user,
                message=f"New application received for {job.job_title} from {request.user.username}"
            )
            
            messages.success(request, f"Application submitted successfully! Your ATS score: {final_score}")
            return redirect('applied_jobs')
    else:
        form = ResumeForm()
    return render(request, 'candidate/apply_job.html', {'form': form, 'job': job})

@login_required
def applied_jobs(request):
    applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    return render(request, 'candidate/applied_jobs.html', {'applications': applications})