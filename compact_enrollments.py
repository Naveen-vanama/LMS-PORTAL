import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from enrollments.models import Enrollment

print("ID | Student | Batch | Status | Date")
print("-" * 50)
for e in Enrollment.objects.all().select_related('student', 'batch').order_by('-id'):
    print(f"{e.id:3} | {e.student.username:10} | {str(e.batch)[:15]:15} | {e.status:10} | {e.enrolled_at.strftime('%Y-%m-%d %H:%M')}")
print("-" * 50)
print(f"Total: {Enrollment.objects.count()}")
