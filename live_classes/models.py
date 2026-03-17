from django.db import models
from django.conf import settings
from courses.models import Course

class LiveClass(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='live_classes')
    batch = models.ForeignKey(
        'courses.Batch', on_delete=models.CASCADE, related_name='live_classes',
        null=True, blank=True,
        help_text='Leave blank to make available to all batches of this course.'
    )
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conducted_live_classes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    scheduled_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    meeting_link = models.URLField(max_length=500, blank=True)
    recording_url = models.FileField(upload_to='live_recordings/', blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.course.title}"

    class Meta:
        verbose_name_plural = "Live Classes"

class LiveClassAttendance(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_class_attendance')
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='attendance')
    join_time = models.DateTimeField(auto_now_add=True)
    leave_time = models.DateTimeField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=0, help_text="Duration in minutes")

    def __str__(self):
        return f"{self.student.username} - {self.live_class.title}"

class LiveChatMessage(models.Model):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name='chat_messages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}: {self.message[:20]}"
