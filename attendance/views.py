from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Case, When, FloatField, Value, Q
from django.db.models.functions import Coalesce

from .models import AttendanceSession, AttendanceRecord
from courses.models import Batch
from enrollments.models import Enrollment


@login_required
def session_list(request, batch_pk):
    batch = get_object_or_404(Batch, pk=batch_pk)
    # Annotate each session with the attendance rate
    sessions = batch.sessions.annotate(
        total_records=Count('records'),
        present_records=Count(Case(When(records__status='present', then=1))),
    ).order_by('-date')
    # Calculate rate as a separate attribute to avoid property collision
    for s in sessions:
        s.rate_val = round((s.present_records / s.total_records * 100), 1) if s.total_records else 0
    return render(request, 'attendance/session_list.html', {
        'batch': batch, 'sessions': sessions
    })


@login_required
def take_attendance(request, batch_pk):
    """Instructor takes attendance for a batch session."""
    batch = get_object_or_404(Batch, pk=batch_pk)
    instructor = batch.course.instructor
    if not (request.user == instructor or request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('attendance:sessions', batch_pk=batch_pk)

    enrolled_students = Enrollment.objects.filter(
        batch=batch, status='active'
    ).select_related('student')

    if request.method == 'POST':
        date = request.POST.get('date')
        topic = request.POST.get('topic', '')
        session, _ = AttendanceSession.objects.get_or_create(
            batch=batch, date=date,
            defaults={'topic': topic, 'created_by': request.user}
        )
        for enrollment in enrolled_students:
            status = request.POST.get(f'status_{enrollment.student_id}', 'absent')
            note = request.POST.get(f'note_{enrollment.student_id}', '')
            AttendanceRecord.objects.update_or_create(
                session=session, student=enrollment.student,
                defaults={'status': status, 'note': note}
            )
        messages.success(request, f'Attendance saved for {date}.')
        return redirect('attendance:sessions', batch_pk=batch_pk)

    return render(request, 'attendance/take_attendance.html', {
        'batch': batch,
        'enrolled_students': enrolled_students,
        'status_choices': AttendanceRecord.AttendanceStatus.choices,
    })


@login_required
def student_report(request, batch_pk):
    """Show a student's attendance report for a batch."""
    import json
    batch = get_object_or_404(Batch, pk=batch_pk)
    student = request.user if request.user.is_student else None
    if 'student_id' in request.GET and not request.user.is_student:
        from users.models import CustomUser
        student = get_object_or_404(CustomUser, pk=request.GET['student_id'])

    sessions = batch.sessions.prefetch_related('records').all()
    records = {
        r.session_id: r for r in AttendanceRecord.objects.filter(
            session__batch=batch, student=student
        )
    } if student else {}

    sessions_ordered = sorted(sessions, key=lambda s: s.date)
    chart_dates = [s.date.strftime("%b %d") for s in sessions_ordered]
    
    present = 0
    absent = 0
    late = 0
    excused = 0
    chart_data = []

    for s in sessions_ordered:
        r = records.get(s.pk)
        if r:
            if r.status == 'present':
                present += 1
                chart_data.append(1)
            elif r.status == 'absent':
                absent += 1
                chart_data.append(0)
            elif r.status == 'late':
                late += 1
                chart_data.append(0.5)
            elif r.status == 'excused':
                excused += 1
                chart_data.append(1)
        else:
            absent += 1
            chart_data.append(0)

    total = len(sessions)
    rate = round(present / total * 100, 1) if total else 0
    
    enrollment = None
    if student:
        enrollment = Enrollment.objects.filter(batch=batch, student=student).first()

    return render(request, 'attendance/student_report.html', {
        'batch': batch,
        'student': student,
        'sessions': sessions,
        'records': records,
        'total': total,
        'present': present,
        'absent': absent,
        'late': late,
        'excused': excused,
        'rate': rate,
        'enrollment': enrollment,
        'chart_dates_json': json.dumps(chart_dates),
        'chart_data_json': json.dumps(chart_data),
    })


@login_required
def my_attendance_summary(request):
    """Summarizes attendance across all active enrollments for the student."""
    import json
    if not request.user.is_student:
        messages.error(request, "Only students can view their attendance summary.")
        return redirect('users:dashboard')

    enrollments = Enrollment.objects.filter(
        student=request.user
    ).exclude(status='dropped').select_related('batch__course')

    # If only one course, redirect directly to its report
    if enrollments.count() == 1:
        return redirect('attendance:report', batch_pk=enrollments.first().batch_id)

    # Otherwise, show a summary page
    summary = []
    course_labels = []
    course_rates = []

    for e in enrollments:
        sessions = AttendanceSession.objects.filter(batch=e.batch)
        total = sessions.count()
        present = AttendanceRecord.objects.filter(
            session__in=sessions,
            student=request.user,
            status='present'
        ).count()
        rate = round(present / total * 100, 1) if total else 0
        summary.append({
            'enrollment': e,
            'total': total,
            'present': present,
            'rate': rate
        })
        course_labels.append(e.batch.course.code)
        course_rates.append(rate)

    return render(request, 'attendance/my_attendance.html', {
        'summary': summary,
        'course_labels_json': json.dumps(course_labels),
        'course_rates_json': json.dumps(course_rates),
    })


@login_required
def manage_attendance_list(request):
    """View to list all batches for attendance management (Admin/Instructor)."""
    if request.user.is_student:
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')

    query = request.GET.get('q', '')
    if request.user.is_instructor:
        batches = Batch.objects.filter(
            course__instructor=request.user
        ).select_related('course').annotate(
            active_students=Count('enrollments', filter=Q(enrollments__status='active')),
            total_sessions=Count('sessions')
        )
    else:
        batches = Batch.objects.select_related('course').annotate(
            active_students=Count('enrollments', filter=Q(enrollments__status='active')),
            total_sessions=Count('sessions')
        )

    if query:
        batches = batches.filter(
            Q(name__icontains=query) |
            Q(course__title__icontains=query) |
            Q(course__code__icontains=query)
        )

    return render(request, 'attendance/manage_attendance_list.html', {
        'batches': batches,
        'query': query
    })
