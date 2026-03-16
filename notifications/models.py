from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LIVE_CLASS_REMINDER = 'LIVE_CLASS_REMINDER', 'Live Class Reminder'
        QUIZ_REMINDER = 'QUIZ_REMINDER', 'Quiz Reminder'
        STREAK_REMINDER = 'STREAK_REMINDER', 'Streak Reminder'
        NEW_LESSON = 'NEW_LESSON', 'New Lesson'
        CERTIFICATE_UNLOCKED = 'CERTIFICATE_UNLOCKED', 'Certificate Unlocked'
        PAYMENT_SUCCESS = 'PAYMENT_SUCCESS', 'Payment Success'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.URLField(max_length=500, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"
