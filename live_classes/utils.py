from django.core.mail import send_mail
from django.conf import settings
from enrollments.models import Enrollment

def send_live_class_notifications(live_class):
    """Notify all enrolled students about a new live class."""
    course = live_class.course
    enrollments = Enrollment.objects.filter(batch__course=course)
    recipient_list = [e.student.email for e in enrollments if e.student.email]
    
    if not recipient_list:
        return
        
    # Ensure scheduled_time is a datetime object
    scheduled_time = live_class.scheduled_time
    if isinstance(scheduled_time, str):
        from django.utils.dateparse import parse_datetime
        scheduled_time = parse_datetime(scheduled_time)
    
    time_str = scheduled_time.strftime('%B %d, %Y at %I:%M %p') if scheduled_time else "TBD"
    
    subject = f"New Live Class scheduled: {live_class.title}"
    message = f"""
    Hello,
    
    A new live class has been scheduled for your course '{course.title}'.
    
    Title: {live_class.title}
    Scheduled Time: {time_str}
    
    You can join the class from your dashboard or by clicking the link below:
    {settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://localhost:8000'}/live-classes/join/{live_class.id}/
    
    Happy Learning!
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=True
        )
    except Exception as e:
        print(f"Error sending live class notifications: {e}")
