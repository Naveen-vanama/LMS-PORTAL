from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from courses.models import Batch


class Enrollment(models.Model):
    """A student enrolled in a specific batch."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        DROPPED = 'dropped', 'Dropped'
        COMPLETED = 'completed', 'Completed'
        WAITLISTED = 'waitlisted', 'Waitlisted'
        PENDING_PAYMENT = 'pending_payment', 'Pending Payment'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'student'},
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='enrollments',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=5, blank=True)   # e.g. A, B+, 85
    
    def clean(self):
        # Prevent enrolling in multiple batches of the same course
        if self.student and self.batch:
            other_enrollments = Enrollment.objects.filter(
                student=self.student,
                batch__course=self.batch.course
            ).exclude(status='dropped')
            
            if self.pk:
                other_enrollments = other_enrollments.exclude(pk=self.pk)
            
            if other_enrollments.exists():
                existing = other_enrollments.first()
                raise ValidationError(f"Student is already enrolled in batch '{existing.batch.name}' for this course. Only one batch per course is allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('student', 'batch')
        ordering = ['-enrolled_at']

    @property
    def total_paid(self):
        from django.db.models import Sum
        result = self.payments.filter(status='completed').aggregate(total=Sum('amount'))['total']
        return result or 0

    @property
    def balance_due(self):
        return self.batch.course.price - self.total_paid

    @property
    def is_paid(self):
        return self.balance_due <= 0

    @property
    def successful_payment(self):
        # Returns the latest completed payment
        return self.payments.filter(status='completed').order_by('-paid_at').first()

    @property
    def progress(self):
        """Calculates course completion percentage based on viewed resources."""
        from resources.models import FileResource, ResourceView
        from django.db.models import Q
        
        course = self.batch.course
        # Students might be enrolled in multiple batches over time, but we care about resources 
        # relevant to their current participation.
        relevant_resources = FileResource.objects.filter(
            course=course, is_visible=True
        ).filter(Q(batch=self.batch) | Q(batch__isnull=True))
        
        total_res = relevant_resources.count()
        if total_res > 0:
            viewed_count = ResourceView.objects.filter(
                student=self.student, resource__in=relevant_resources
            ).count()
            return round((viewed_count / total_res) * 100)
        return 0

    def __str__(self):
        return f"{self.student.username} → {self.batch}"
