from django.db import models
from django.conf import settings
from courses.models import Batch


class AttendanceSession(models.Model):
    """A single class session where attendance is taken."""

    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    topic = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='attendance_sessions',
    )

    class Meta:
        unique_together = ('batch', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.batch} – {self.date}"

    @property
    def attendance_rate(self):
        total = self.records.count()
        present = self.records.filter(status='present').count()
        return round((present / total * 100), 1) if total else 0


class AttendanceRecord(models.Model):
    """Attendance status for a single student in a session."""

    class AttendanceStatus(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        LATE = 'late', 'Late'
        EXCUSED = 'excused', 'Excused'

    session = models.ForeignKey(
        AttendanceSession, on_delete=models.CASCADE, related_name='records'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='attendance_records',
        limit_choices_to={'role': 'student'},
    )
    status = models.CharField(
        max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.ABSENT
    )
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student.username} – {self.session.date}: {self.status}"
