from django.db import models
from django.conf import settings
from courses.models import Course, Lesson

class UserActivity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    activity_date = models.DateField(db_index=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    lessons_completed = models.ManyToManyField(Lesson, blank=True)
    
    class Meta:
        unique_together = ('user', 'activity_date')

    def __str__(self):
        return f"{self.user.username} - {self.activity_date}"

class CourseAnalyticsCache(models.Model):
    """Stores cached analytics for courses to speed up instructor dashboard."""
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='analytics_cache')
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cache for {self.course.title}"
