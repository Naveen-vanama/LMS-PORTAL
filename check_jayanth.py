import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from enrollments.models import Enrollment

print("--- User Check ---")
user = CustomUser.objects.filter(username='jayanth').first()
if user:
    print(f"Username: {user.username}")
    print(f"Role: {user.role}")
    print(f"Is active: {user.is_active}")
else:
    print("User 'jayanth' does not exist.")

print("\n--- Enrollment Check ---")
if user:
    enrollments = Enrollment.objects.filter(student=user)
    print(f"Enrollments for jayanth: {enrollments.count()}")
    for e in enrollments:
        print(f" - Enrolled in: {e.batch} | status: {e.status}")
else:
    print("Cannot check enrollments: User not found.")

print("\n--- All Enrollments ---")
all_e = Enrollment.objects.all().select_related('student', 'batch')
for e in all_e:
    print(f"{e.student.username} -> {e.batch} | status: {e.status}")
