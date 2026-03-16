from .models import Notification
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

def notify_user(user, title, message, n_type, link=None, send_email=False):
    """
    Creates a notification for a user and optionally sends an email and real-time update.
    """
    # Create database record
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=n_type,
        link=link
    )

    # Real-time update via Django Channels
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f"user_{user.id}",
            {
                "type": "notification_message",
                "notification": {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.notification_type,
                    "link": notification.link,
                    "created_at": notification.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        )

    # Optional Email Notification
    if send_email and user.email:
        try:
            send_mail(
                subject=title,
                message=message + (f"\n\nLink: {link}" if link else ""),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception as e:
            print(f"Error sending email: {e}")

    return notification
