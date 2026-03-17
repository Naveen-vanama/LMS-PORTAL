from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from courses.models import Batch
from .models import Enrollment
from users.models import CustomUser


@login_required
def enroll(request, batch_pk):
    """Student self-enrollment."""
    batch = get_object_or_404(Batch, pk=batch_pk)
    if not request.user.is_student:
        messages.error(request, 'Only students can enroll.')
        return redirect('courses:detail', pk=batch.course_id)

    # Check if student is already enrolled in another batch of THIS course
    already_enrolled = Enrollment.objects.filter(
        student=request.user,
        batch__course=batch.course
    ).exclude(status=Enrollment.Status.DROPPED).first()

    if already_enrolled:
        if already_enrolled.batch == batch:
            messages.info(request, 'You are already enrolled in this batch.')
        else:
            messages.warning(request, f'You are already enrolled in batch "{already_enrolled.batch.name}" for this course. You can only enroll in one batch per course.')
        return redirect('courses:detail', pk=batch.course_id)

    if batch.is_full:
        messages.warning(request, 'This batch is full. Added to waitlist.')
        status = Enrollment.Status.WAITLISTED
    elif batch.course.price > 0:
        status = Enrollment.Status.PENDING_PAYMENT
    else:
        status = Enrollment.Status.PENDING_APPROVAL

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, batch=batch,
        defaults={'status': status}
    )

    if created:
        if status == Enrollment.Status.PENDING_PAYMENT:
            messages.info(request, f'Step 1: Enrollment created. Please complete the payment to activate your seat.')
            return redirect('payments:checkout', enrollment_pk=enrollment.pk)
        elif status == Enrollment.Status.PENDING_APPROVAL:
            messages.success(request, f'Enrollment request submitted for {batch}. Awaiting admin approval.')
        else:
            messages.success(request, f'Enrolled in {batch} successfully!')
    else:
        if enrollment.status == Enrollment.Status.PENDING_PAYMENT:
            return redirect('payments:checkout', enrollment_pk=enrollment.pk)
        messages.info(request, 'You are already enrolled in this batch.')
    return redirect('courses:detail', pk=batch.course_id)


@login_required
def unenroll(request, batch_pk):
    """Prevents students from dropping courses as per new requirement."""
    if request.user.is_student:
        messages.error(request, 'Students are not allowed to drop courses once enrolled. Please contact an administrator.')
        batch = get_object_or_404(Batch, pk=batch_pk)
        return redirect('courses:detail', pk=batch.course_id)
        
    batch = get_object_or_404(Batch, pk=batch_pk)
    Enrollment.objects.filter(student=request.user, batch=batch).update(
        status=Enrollment.Status.DROPPED
    )
    messages.info(request, f'Dropped from {batch}.')
    return redirect('courses:detail', pk=batch.course_id)


@login_required
def enrollment_list(request):
    """Admin / instructor view of all enrollments."""
    query = request.GET.get('q', '')

    if request.user.is_student:
        enrollments = Enrollment.objects.filter(
            student=request.user
        ).select_related('batch__course', 'batch__course__instructor', 'certificate')
    elif request.user.is_instructor:
        enrollments = Enrollment.objects.filter(
            batch__course__instructor=request.user
        ).select_related('student', 'batch__course', 'certificate')
    else:
        enrollments = Enrollment.objects.select_related(
            'student', 'batch__course', 'certificate'
        ).order_by('-enrolled_at')

    if query:
        enrollments = enrollments.filter(
            Q(student__username__icontains=query) |
            Q(student__first_name__icontains=query) |
            Q(student__last_name__icontains=query) |
            Q(student__email__icontains=query) |
            Q(batch__course__title__icontains=query) |
            Q(batch__course__code__icontains=query) |
            Q(batch__name__icontains=query)
        )

    return render(request, 'enrollments/enrollment_list.html', {
        'enrollments': enrollments,
        'query': query
    })


@login_required
def grade_update(request, pk):
    """Instructor updates a student's grade."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if not (request.user == enrollment.batch.course.instructor or
            request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('enrollments:list')

    if request.method == 'POST':
        grade = request.POST.get('grade', '').strip()
        enrollment.grade = grade
        enrollment.save(update_fields=['grade'])
        messages.success(request, 'Grade updated.')
    return redirect('enrollments:list')


@login_required
def mark_complete(request, pk):
    """Instructor/Admin marks an enrollment as completed."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if not (request.user == enrollment.batch.course.instructor or
            request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('enrollments:list')
    if request.method == 'POST':
        enrollment.status = Enrollment.Status.COMPLETED
        enrollment.save(update_fields=['status'])
        
        # Auto-issue certificate if they qualify
        from certificates.utils import issue_certificate
        cert, created, error = issue_certificate(enrollment)
        
        # Trigger Notifications
        from notifications.services import notify_user
        from django.urls import reverse
        
        notify_user(
            user=enrollment.student,
            title="Course Completed!",
            message=f"Congratulations! You have successfully completed the course '{enrollment.batch.course.title}'.",
            n_type='CERTIFICATE_UNLOCKED',
            link=reverse('users:dashboard')
        )
        
        if created:
            notify_user(
                user=enrollment.student,
                title="Certificate Issued",
                message=f"A certificate has been issued for your completion of '{enrollment.batch.course.title}'.",
                n_type='CERTIFICATE_UNLOCKED',
                link=reverse('enrollments:list'),
                send_email=True
            )
            messages.success(request, f'Marked {enrollment.student.get_full_name() or enrollment.student.username} as Completed. ✅ Certificate issued (ID: {cert.certificate_id}).')
        elif error:
            messages.warning(request, f'Marked as Completed, but certificate not issued: {error}')
        else:
            messages.success(request, f'Marked {enrollment.student.get_full_name() or enrollment.student.username} as Completed.')
    return redirect('enrollments:list')

@login_required
def approve_enrollment(request, pk):
    """Instructor/Admin approves a pending enrollment."""
    enrollment = get_object_or_404(Enrollment, pk=pk)
    if not (request.user == enrollment.batch.course.instructor or
            request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('enrollments:list')
    
    if request.method == 'POST':
        if enrollment.status in [Enrollment.Status.PENDING_APPROVAL, Enrollment.Status.WAITLISTED]:
            enrollment.status = Enrollment.Status.ACTIVE
            enrollment.save(update_fields=['status'])
            messages.success(request, f'Enrollment for {enrollment.student.get_full_name() or enrollment.student.username} approved.')
        else:
            messages.warning(request, f'Cannot approve an enrollment with status: {enrollment.get_status_display()}')
    return redirect('enrollments:list')
