from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, F, FloatField
from django.db.models.functions import Coalesce
from django.utils import timezone

from .forms import LoginForm, RegisterForm, ProfileUpdateForm
from .models import CustomUser
from courses.models import Course, Batch, Announcement
from enrollments.models import Enrollment
from attendance.models import AttendanceRecord
from payments.models import Payment
from resources.models import FileResource, ResourceView
from quizzes.models import StudentStreak, StudentBadge
from quizzes.streak_logic import get_streak_calendar
from live_classes.models import LiveClass
from django.core.mail import send_mail


def login_view(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
        next_url = request.GET.get('next', 'users:dashboard')
        return redirect(next_url)

    return render(request, 'users/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('users:login')


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('users:dashboard')
    return render(request, 'users/register.html', {'form': form})


@login_required
def dashboard_view(request):
    import json
    user = request.user
    today = timezone.now().date()
    context = {'user': user, 'today': today}

    if user.is_admin_role or user.is_superuser:
        total_students = CustomUser.objects.filter(role='student').count()
        total_instructors = CustomUser.objects.filter(role='instructor').count()
        total_admins = CustomUser.objects.filter(role='admin').count() + CustomUser.objects.filter(is_superuser=True, role='').count()

        top_courses = Course.objects.annotate(
            enrollment_count=Count('batches__enrollments')
        ).order_by('-enrollment_count')[:5]

        context.update({
            'total_users': CustomUser.objects.count(),
            'total_courses': Course.objects.count(),
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_batches': Batch.objects.count(),
            'total_active_enrollments': Enrollment.objects.filter(status='active').count(),
            'recent_enrollments': Enrollment.objects.select_related(
                'student', 'batch__course'
            ).order_by('-enrolled_at')[:10],
            'courses': Course.objects.order_by('-created_at')[:5],
            'total_payments_amount': sum(p.amount for p in Payment.objects.filter(status='completed')),
            'top_courses_labels_json': json.dumps([c.code for c in top_courses]),
            'top_courses_data_json': json.dumps([c.enrollment_count for c in top_courses]),
            'at_risk_students': CustomUser.objects.filter(role='student').annotate(
                total_attn=Count('attendance_records'),
                present_attn=Count('attendance_records', filter=Q(attendance_records__status='present'))
            ).filter(total_attn__gte=3).annotate(
                attn_rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present')) / Count('attendance_records'), 0.0, output_field=FloatField())
            ).filter(attn_rate__lt=75).order_by('attn_rate')[:5],
            'risk_pie_labels_json': json.dumps(['On Track', 'At Risk']),
            'risk_pie_data_json': json.dumps([
                CustomUser.objects.filter(role='student').annotate(
                    total_attn=Count('attendance_records'),
                ).filter(total_attn__gte=3).annotate(
                    rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present')) / Count('attendance_records'), 0.0, output_field=FloatField())
                ).filter(rate__gte=75).count(),
                CustomUser.objects.filter(role='student').annotate(
                    total_attn=Count('attendance_records'),
                ).filter(total_attn__gte=3).annotate(
                    rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present')) / Count('attendance_records'), 0.0, output_field=FloatField())
                ).filter(rate__lt=75).count()
            ]),
        })

    elif user.is_instructor:
        instructor_courses = Course.objects.filter(
            instructor=user
        ).annotate(enrollment_count=Count('batches__enrollments'))
        total_batches = Batch.objects.filter(course__instructor=user).count()
        recent_enrollments = Enrollment.objects.filter(
            batch__course__instructor=user
        ).select_related('student', 'batch__course').order_by('-enrolled_at')[:8]
        
        c_labels = [c.code for c in instructor_courses]
        c_data = [c.enrollment_count for c in instructor_courses]

        context.update({
            'courses': instructor_courses,
            'total_students': Enrollment.objects.filter(
                batch__course__instructor=user,
                status='active',
            ).values('student').distinct().count(),
            'total_batches': total_batches,
            'recent_batches': Batch.objects.filter(
                course__instructor=user
            ).order_by('-created_at')[:5],
            'recent_enrollments': recent_enrollments,
            'recent_announcements': Announcement.objects.filter(
                course__instructor=user
            ).order_by('-created_at')[:5],
            'course_labels_json': json.dumps(c_labels),
            'course_data_json': json.dumps(c_data),
            'at_risk_students': CustomUser.objects.filter(
                role='student',
                enrollments__batch__course__instructor=user
            ).distinct().annotate(
                total_attn=Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)),
            ).filter(total_attn__gte=3).annotate(
                attn_rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present', attendance_records__session__batch__course__instructor=user)) / Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)), 0.0, output_field=FloatField())
            ).filter(attn_rate__lt=75).order_by('attn_rate')[:5],
            'risk_pie_labels_json': json.dumps(['On Track', 'At Risk']),
            'risk_pie_data_json': json.dumps([
                CustomUser.objects.filter(role='student', enrollments__batch__course__instructor=user).distinct().annotate(
                    total_attn=Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)),
                ).filter(total_attn__gte=3).annotate(
                    rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present', attendance_records__session__batch__course__instructor=user)) / Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)), 0.0, output_field=FloatField())
                ).filter(rate__gte=75).count(),
                CustomUser.objects.filter(role='student', enrollments__batch__course__instructor=user).distinct().annotate(
                    total_attn=Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)),
                ).filter(total_attn__gte=3).annotate(
                    rate=Coalesce(100.0 * Count('attendance_records', filter=Q(attendance_records__status='present', attendance_records__session__batch__course__instructor=user)) / Count('attendance_records', filter=Q(attendance_records__session__batch__course__instructor=user)), 0.0, output_field=FloatField())
                ).filter(rate__lt=75).count()
            ]),
        })

    else:  # Student
        enrollments = Enrollment.objects.filter(
            student=user
        ).select_related('batch__course', 'batch__course__instructor', 'certificate')

        # Add course progress to each enrollment object
        progress_labels = []
        progress_data = []

        for e in enrollments:
            progress_labels.append(e.batch.course.code)
            progress_data.append(e.progress)

        # Attendance stats
        total_records = AttendanceRecord.objects.filter(student=user).count()
        present_records = AttendanceRecord.objects.filter(
            student=user, status='present'
        ).count()
        attendance_percentage = round(
            (present_records / total_records * 100), 1
        ) if total_records else None

        missed_records = total_records - present_records

        missed_records = total_records - present_records
        if attendance_percentage is not None and attendance_percentage < 70:
            if request.session.get('attendance_alert_date') != str(today) and user.email:
                subject = "Attendance Warning - CollegePortal"
                message = f"Dear {user.get_full_name() or user.username},\n\nThis is an automated alert from CollegePortal. Your overall attendance has dropped to {attendance_percentage}%, which is below the 70% requirement. Please refer to your dashboard for further details.\n\nRegards,\nCollegePortal Team"
                try:
                    send_mail(subject, message, None, [user.email], fail_silently=True)
                except Exception:
                    pass
                request.session['attendance_alert_date'] = str(today)

        active_count = enrollments.filter(status='active').count()
        completed_count = enrollments.filter(status='completed').count()
        
        # Latest announcements from all enrolled courses
        enrolled_course_ids = enrollments.values_list('batch__course_id', flat=True)
        announcements = Announcement.objects.filter(
            Q(course_id__in=enrolled_course_ids),
            Q(batch__in=enrollments.values_list('batch_id', flat=True)) | Q(batch__isnull=True)
        ).select_related('course', 'author').order_by('-created_at')[:8]

        earned_certificates_count = enrollments.filter(certificate__isnull=False).count()
        
        context.update({
            'enrollments': enrollments,
            'total_courses': enrollments.count(),
            'active_courses_count': active_count,
            'completed_courses_count': completed_count,
            'earned_certificates_count': earned_certificates_count,
            'attendance_percentage': attendance_percentage,
            'risk_pie_labels_json': json.dumps(['Attended', 'Missed']),
            'risk_pie_data_json': json.dumps([present_records, missed_records]),
            'risk_on_track_count': present_records,
            'risk_at_risk_count': missed_records,
            'announcements': announcements,
            'progress_labels_json': json.dumps(progress_labels),
            'progress_data_json': json.dumps(progress_data),
        })

        # Add Quiz Streak Data
        
        streak_obj = StudentStreak.objects.filter(student=user).first()
        streak_calendar = get_streak_calendar(user)
        badges = StudentBadge.objects.filter(student=user).order_by('-earned_date')
        
        context.update({
            'streak': streak_obj,
            'streak_calendar': streak_calendar,
            'badges': badges,
            'taken_quiz_today': (streak_obj.last_quiz_date == today) if streak_obj else False
        })
        
        # Add Live Class Data
        enrolled_courses = Enrollment.objects.filter(student=user).values_list('batch__course', flat=True)
        upcoming_live_sessions = LiveClass.objects.filter(
            course_id__in=enrolled_courses,
            scheduled_time__gte=timezone.now()
        ).order_by('scheduled_time')[:5]
        
        context.update({
            'upcoming_live_sessions': upcoming_live_sessions
        })

    return render(request, 'users/dashboard.html', context)


import random
import string
from django.core.mail import send_mail
from datetime import timedelta

def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        user = CustomUser.objects.filter(email=email).first()
        if user:
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp = otp
            user.otp_expiry = timezone.now() + timedelta(minutes=10)
            user.save()
            
            # Send Email
            subject = "Your Password Reset OTP"
            message = f"Your OTP for password reset is: {otp}. It will expire in 10 minutes."
            send_mail(subject, message, None, [email])
            
            request.session['reset_email'] = email
            request.session['last_otp_sent'] = timezone.now().timestamp()
            messages.success(request, 'An OTP has been sent to your email.')
            return redirect('users:password_reset_verify')
        else:
            messages.error(request, 'No user found with this email.')
            
    return render(request, 'users/password_reset_request.html')


def password_reset_verify(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('users:password_reset_request')
        
    last_sent = request.session.get('last_otp_sent', 0)
    now = timezone.now().timestamp()
    remaining = max(0, int(60 - (now - last_sent)))

    if request.method == 'POST':
        otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = CustomUser.objects.filter(email=email).first()
        if user and user.otp == otp and user.otp_expiry > timezone.now():
            if new_password == confirm_password:
                user.set_password(new_password)
                user.otp = None
                user.otp_expiry = None
                user.save()
                messages.success(request, 'Password reset successful. Please login.')
                del request.session['reset_email']
                del request.session['last_otp_sent']
                return redirect('users:login')
            else:
                messages.error(request, 'Passwords do not match.')
        else:
            messages.error(request, 'Invalid or expired OTP.')
            
    return render(request, 'users/password_reset_verify.html', {
        'email': email,
        'remaining_cooldown': remaining
    })


def resend_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('users:password_reset_request')
        
    last_sent = request.session.get('last_otp_sent', 0)
    now = timezone.now().timestamp()
    if now - last_sent < 60:
        messages.error(request, f'Please wait {int(60 - (now - last_sent))} seconds before resending.')
        return redirect('users:password_reset_verify')

    user = CustomUser.objects.filter(email=email).first()
    if user:
        otp = ''.join(random.choices(string.digits, k=6))
        user.otp = otp
        user.otp_expiry = timezone.now() + timedelta(minutes=10)
        user.save()
        
        send_mail("New Password Reset OTP", f"Your new OTP is: {otp}", None, [email])
        request.session['last_otp_sent'] = timezone.now().timestamp()
        messages.success(request, 'A new OTP has been sent.')
    else:
        messages.error(request, 'User not found.')
        
    return redirect('users:password_reset_verify')


@login_required
def profile_view(request):
    form = ProfileUpdateForm(
        request.POST or None,
        request.FILES or None,
        instance=request.user
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    return render(request, 'users/profile.html', {'form': form})


@login_required
def user_list_view(request):
    """Admin view to see all students and instructors."""
    if not (request.user.is_admin_role or request.user.is_superuser):
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')
    
    role_filter = request.GET.get('role', '')
    query = request.GET.get('q', '')
    users = CustomUser.objects.all().order_by('role', 'username')

    if role_filter:
        users = users.filter(role=role_filter)

    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).distinct()

    return render(request, 'users/user_list.html', {
        'users': users,
        'role_filter': role_filter,
        'query': query,
    })
