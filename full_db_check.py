import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from enrollments.models import Enrollment

print("--- ALL USERS ---")
for u in CustomUser.objects.all().order_by('username'):
    print(f"{u.username:15} | role: {u.role:10} | super: {u.is_superuser}")

print("\n--- ALL ENROLLMENTS ---")
for e in Enrollment.objects.all().select_related('student', 'batch').order_by('-enrolled_at'):
    print(f"{e.student.username:15} -> {str(e.batch):30} | status: {e.status}")
