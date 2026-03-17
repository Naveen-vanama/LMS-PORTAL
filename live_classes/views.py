from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import LiveClass, LiveClassAttendance, LiveChatMessage
from courses.models import Course, Batch
from enrollments.models import Enrollment
from .utils import send_live_class_notifications

@login_required
def live_class_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Check if student is enrolled or user is instructor/admin
    is_instructor = (course.instructor == request.user) or request.user.is_instructor or request.user.is_staff
    is_enrolled = Enrollment.objects.filter(student=request.user, batch__course=course, status='active').exists()
    
    if not (is_instructor or is_enrolled):
        messages.error(request, "You are not authorized to view live classes for this course.")
        return redirect('courses:detail', pk=course_id)
        
    classes = course.live_classes.all()
    if request.user.is_student:
        enrolled_batch_ids = Enrollment.objects.filter(
            student=request.user, batch__course=course, status='active'
        ).values_list('batch_id', flat=True)
        classes = classes.filter(Q(batch__in=enrolled_batch_ids) | Q(batch__isnull=True))
    
    upcoming_classes = classes.filter(scheduled_time__gte=timezone.now()).order_by('scheduled_time')
    past_classes = classes.filter(scheduled_time__lt=timezone.now()).order_by('-scheduled_time')
    
    return render(request, 'live_classes/class_list.html', {
        'course': course,
        'upcoming_classes': upcoming_classes,
        'past_classes': past_classes,
        'is_instructor': is_instructor
    })

@login_required
def schedule_class(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if not (course.instructor == request.user or request.user.is_staff):
        messages.error(request, "Only the instructor can schedule live classes.")
        return redirect('courses:detail', pk=course_id)
        
    if request.method == "POST":
        title = request.POST.get('title')
        description = request.POST.get('description')
        scheduled_time = request.POST.get('scheduled_time')
        duration = request.POST.get('duration')
        batch_id = request.POST.get('batch')
        batch = None
        if batch_id:
            batch = get_object_or_404(Batch, id=batch_id, course=course)
        
        # Room name for Jitsi
        safe_title = "".join(x for x in title if x.isalnum())
        room_name = f"CollegePortal_{course.id}_{safe_title}_{timezone.now().strftime('%Y%m%d%H%M')}"
        meeting_link = f"https://meet.jit.si/{room_name}"
        
        live_class = LiveClass.objects.create(
            course=course,
            batch=batch,
            instructor=request.user,
            title=title,
            description=description,
            scheduled_time=scheduled_time,
            duration=duration,
            meeting_link=meeting_link
        )
        
        # Trigger Notifications for all enrolled students
        from notifications.services import notify_user
        from django.urls import reverse
        
        enrolled_students = Enrollment.objects.filter(batch__course=course, status='active')
        if batch:
            enrolled_students = enrolled_students.filter(batch=batch)
        enrolled_students = enrolled_students.select_related('student')
        for enrollment in enrolled_students:
            notify_user(
                user=enrollment.student,
                title="New Live Class Scheduled",
                message=f"A new live class '{title}' has been scheduled for {course.code}.",
                n_type='LIVE_CLASS_REMINDER',
                link=reverse('live_classes:list', kwargs={'course_id': course.id}),
                send_email=True
            )
        
        messages.success(request, f"Live class '{title}' scheduled successfully!")
        return redirect('live_classes:list', course_id=course.id)
        
    batches = course.batches.all()
    return render(request, 'live_classes/schedule_form.html', {'course': course, 'batches': batches})

@login_required
def join_class(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)
    course = live_class.course
    
    # Check enrollment/instructor
    is_instructor = (course.instructor == request.user) or request.user.is_instructor or request.user.is_staff
    is_enrolled = Enrollment.objects.filter(student=request.user, batch__course=course, status='active').exists()
    
    if request.user.is_student:
        # Check if this specific class is for student's batch
        batch_ids = Enrollment.objects.filter(
            student=request.user, batch__course=course, status='active'
        ).values_list('batch_id', flat=True)
        if live_class.batch and live_class.batch_id not in batch_ids:
            messages.error(request, "Access denied. This class is not for your batch.")
            return redirect('live_classes:list', course_id=course.id)

    if not (is_instructor or is_enrolled):
        messages.error(request, "You are not authorized to join this live class.")
        return redirect('courses:list')
    
    chat_history = live_class.chat_messages.all().order_by('timestamp')
    
    return render(request, 'live_classes/join_session.html', {
        'live_class': live_class,
        'is_instructor': is_instructor,
        'chat_history': chat_history
    })

@login_required
def end_class(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)
    if live_class.instructor != request.user and not request.user.is_staff:
        return redirect('live_classes:list', course_id=live_class.course.id)
    
    live_class.is_active = False
    live_class.save()
    
    # Update leave time for all attendees who haven't left
    LiveClassAttendance.objects.filter(live_class=live_class, leave_time__isnull=True).update(leave_time=timezone.now())
    
    messages.success(request, "Live class sessions ended.")
    return redirect('live_classes:list', course_id=live_class.course.id)

@login_required
def upload_recording(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)
    if live_class.instructor != request.user and not request.user.is_staff:
        return redirect('live_classes:list', course_id=live_class.course.id)
        
    if request.method == "POST" and request.FILES.get('recording'):
        live_class.recording_url = request.FILES.get('recording')
        live_class.save()
        messages.success(request, "Recording uploaded successfully!")
        
    return redirect('live_classes:list', course_id=live_class.course.id)

@login_required
def view_attendance(request, class_id):
    live_class = get_object_or_404(LiveClass, id=class_id)
    if live_class.instructor != request.user and not request.user.is_staff:
        return redirect('live_classes:list', course_id=live_class.course.id)
        
    attendances = live_class.attendance.all().order_by('student__username')
    return render(request, 'live_classes/attendance_list.html', {
        'live_class': live_class,
        'attendances': attendances
    })
