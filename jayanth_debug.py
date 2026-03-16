import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from enrollments.models import Enrollment
from courses.models import Batch

print("--- JAYANTH STATUS ---")
j = CustomUser.objects.filter(username='jayanth').first()
if j:
    print(f"User: {j.username} (ID: {j.id})")
    print(f"Role: {j.role}")
    enrollments = Enrollment.objects.filter(student=j).select_related('batch__course__instructor')
    print(f"Enrollment Count: {enrollments.count()}")
    for e in enrollments:
        print(f" - Batch: {e.batch.name} | Course: {e.batch.course.title} | Instructor: {e.batch.course.instructor.username}")
else:
    print("User jayanth not found.")

print("\n--- INSTRUCTORS ---")
instructors = CustomUser.objects.filter(role='instructor')
for i in instructors:
    print(f"Instructor: {i.username} ({i.get_full_name()})")

print("\n--- RECENT ENROLLMENTS (All) ---")
all_e = Enrollment.objects.all().select_related('student', 'batch__course__instructor').order_by('-enrolled_at')[:10]
for e in all_e:
    print(f"{e.student.username:15} -> {e.batch.course.title:20} ({e.batch.name}) | Inst: {e.batch.course.instructor.username}")
