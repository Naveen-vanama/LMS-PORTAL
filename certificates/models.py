from django.db import models
from django.utils import timezone
from enrollments.models import Enrollment
import uuid

from django.conf import settings
import uuid

class Certificate(models.Model):
    """A certificate earned by a student upon meeting course criteria."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='certificate'
    )
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='earned_certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='issued_certificates')
    
    certificate_id = models.CharField(max_length=50, unique=True, blank=True)
    completion_percentage = models.FloatField(default=0.0)
    issued_date = models.DateTimeField(auto_now_add=True)
    certificate_pdf = models.FileField(upload_to='certificates/pdfs/', blank=True, null=True)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        ordering = ['-issued_date']

    def __str__(self):
        return f"{self.certificate_id} - {self.student.username}"

    def save(self, *args, **kwargs):
        if not self.certificate_id:
            # Short human-readable ID
            year = timezone.now().year
            short_id = str(self.id).split('-')[0].upper()
            self.certificate_id = f"CERT-{year}-{short_id}"
        
        # Ensure student and course are mirrored from enrollment
        if not self.student_id:
            self.student = self.enrollment.student
        if not self.course_id:
            self.course = self.enrollment.batch.course
            
        super().save(*args, **kwargs)

