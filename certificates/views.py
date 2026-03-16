from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q

from enrollments.models import Enrollment
from attendance.models import AttendanceRecord, AttendanceSession
from .models import Certificate
from .utils import generate_certificate_pdf, issue_certificate
from django.core.files.base import ContentFile


@login_required
def check_and_issue_certificate(request, enrollment_id):
    """Manual trigger for certificate issuance with PDF generation."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    
    # Permission check: Student can issue THEIR OWN if eligible
    if request.user.role == 'student' and enrollment.student != request.user:
         messages.error(request, 'Unauthorized access.')
         return redirect('users:dashboard')
    
    cert, created, error = issue_certificate(enrollment)
    
    if error:
        messages.warning(request, error)
    else:
        pdf_content = generate_certificate_pdf(cert)
        cert.certificate_pdf.save(
            f"certificate_{cert.certificate_id}.pdf",
            ContentFile(pdf_content),
            save=True
        )
        
        if created:
            messages.success(request, f'Certificate {cert.certificate_id} issued successfully!')
        else:
            messages.info(request, f'Certificate {cert.certificate_id} already exists (PDF refreshed).')
            
    return redirect('users:dashboard' if request.user.role == 'student' else 'enrollments:list')


@login_required
def download_certificate(request, certificate_id):
    """Downloads the generated PDF certificate."""
    try:
        certificate = Certificate.objects.select_related(
            'enrollment__student',
            'enrollment__batch__course__instructor'
        ).get(certificate_id=certificate_id)
    except Certificate.DoesNotExist:
        messages.error(request, 'Certificate not found.')
        return redirect('users:dashboard')
    
    # Must be the student who earned it, or admin/instructor
    is_owner = request.user == certificate.enrollment.student
    is_instructor = request.user == certificate.enrollment.batch.course.instructor
    is_admin = request.user.is_admin_role or request.user.is_superuser
    
    if not (is_owner or is_instructor or is_admin):
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')

    # Generate the PDF
    pdf_bytes = generate_certificate_pdf(certificate)
    
    # Stream PDF as download
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    from django.utils.text import slugify
    course_name = slugify(certificate.course.title).replace('-', '_')
    filename = f"certificate_{course_name}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
@login_required
def certificate_list(request):
    """View to list all issued certificates (Admin/Instructor only)."""
    if request.user.is_student:
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')

    query = request.GET.get('q', '')
    if request.user.is_instructor:
        certificates = Certificate.objects.filter(
            enrollment__batch__course__instructor=request.user
        ).select_related('enrollment__student', 'enrollment__batch__course')
    else:
        certificates = Certificate.objects.select_related(
            'enrollment__student', 'enrollment__batch__course'
        )

    if query:
        certificates = certificates.filter(
            Q(enrollment__student__username__icontains=query) |
            Q(enrollment__student__first_name__icontains=query) |
            Q(enrollment__student__last_name__icontains=query) |
            Q(enrollment__batch__course__title__icontains=query) |
            Q(certificate_id__icontains=query)
        )

    return render(request, 'certificates/certificate_list.html', {
        'certificates': certificates,
        'query': query
    })

def verify_certificate(request, certificate_id):
    """Publicly verifies a certificate using its UUID."""
    certificate = get_object_or_404(
        Certificate.objects.select_related('student', 'course', 'course__instructor'),
        id=certificate_id
    )
    return render(request, 'certificates/verify.html', {
        'cert': certificate,
        'is_valid': True
    })
