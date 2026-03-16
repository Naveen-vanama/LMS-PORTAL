import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from courses.models import Course, Batch
from enrollments.models import Enrollment
from attendance.models import AttendanceSession, AttendanceRecord

print('USERS:')
for u in CustomUser.objects.all():
    print(u.username, u.role, u.is_superuser)

print('COURSES:')
for c in Course.objects.all():
    print(c.code, c.instructor)

print('BATCHES:')
for b in Batch.objects.all():
    print(b, b.course.instructor)

print('ENROLLMENTS:')
for e in Enrollment.objects.all():
    print(e.student.username, '->', str(e.batch), 'status:', e.status)

print('ATTENDANCE RECORDS:')
for r in AttendanceRecord.objects.all():
    print(r.student.username, r.session.date, r.status)
