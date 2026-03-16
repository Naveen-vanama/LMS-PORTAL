from django.db import models
from django.conf import settings
from courses.models import Course, Batch


class FileResource(models.Model):
    """A file uploaded for a course or specific batch."""

    class ResourceType(models.TextChoices):
        LECTURE = 'lecture', 'Lecture Slide'
        ASSIGNMENT = 'assignment', 'Assignment'
        READING = 'reading', 'Reading Material'
        VIDEO_LINK = 'video', 'Video Link'
        OTHER = 'other', 'Other'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(
        max_length=20, choices=ResourceType.choices, default=ResourceType.OTHER
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name='resources'
    )
    batch = models.ForeignKey(
        Batch, on_delete=models.CASCADE, related_name='resources',
        null=True, blank=True,
        help_text='Leave blank to make available to all batches of this course.'
    )
    file = models.FileField(upload_to='resources/%Y/%m/', blank=True, null=True)
    external_url = models.URLField(blank=True)   # for video links etc.
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='uploaded_resources',
    )
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_resource_type_display()}] {self.title}"

    @property
    def download_url(self):
        if self.file:
            return self.file.url
        return self.external_url


class ResourceView(models.Model):
    """Tracks which student has viewed which resource."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='viewed_resources'
    )
    resource = models.ForeignKey(
        FileResource, on_delete=models.CASCADE,
        related_name='views'
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'resource')

    def __str__(self):
        return f"{self.student.username} viewed {self.resource.title}"
