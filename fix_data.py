import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from courses.models import Course, Batch
from enrollments.models import Enrollment
from attendance.models import AttendanceSession, AttendanceRecord
from certificates.models import Certificate
import datetime

print("=== FIXING DATA ===")

# 1. Fix admin user role
admin = CustomUser.objects.get(username='admin')
admin.role = 'admin'
admin.first_name = 'System'
admin.last_name = 'Admin'
admin.save()
print(f"Fixed admin role: {admin.role}")

# 2. Fix instructor
instructor = CustomUser.objects.get(username='prof_smith')
print(f"Instructor: {instructor.get_full_name()} | role={instructor.role}")

# 3. Ensure we have at least 3 students
students = list(CustomUser.objects.filter(role='student'))
print(f"Students: {[s.username for s in students]}")

# 4. Ensure courses exist
courses = list(Course.objects.all())
if len(courses) < 2:
    print("Creating missing courses...")
    if not Course.objects.filter(code='CS101').exists():
        Course.objects.create(title='Intro to Programming', code='CS101', description='Python basics.', instructor=instructor)
    if not Course.objects.filter(code='CS201').exists():
        Course.objects.create(title='Data Structures', code='CS201', description='Advanced DS.', instructor=instructor)
    courses = list(Course.objects.all())

for c in courses:
    print(f"Course: {c.code} | instructor={c.instructor}")

# 5. Ensure batches exist
batches = list(Batch.objects.all())
if not batches:
    print("Creating batches...")
    b1 = Batch.objects.create(course=courses[0], name='Fall 2026', start_date=datetime.date(2026,9,1), end_date=datetime.date(2026,12,15))
    b2 = Batch.objects.create(course=courses[1], name='Spring 2026', start_date=datetime.date(2026,1,15), end_date=datetime.date(2026,5,15))
    batches = [b1, b2]
else:
    b1, b2 = batches[0], batches[1] if len(batches) > 1 else batches[0]

print(f"Batches: {[str(b) for b in batches]}")

# 6. Enroll students in batches
for student in students[:2]:
    e, created = Enrollment.objects.get_or_create(student=student, batch=b1, defaults={'status': 'active'})
    if created:
        print(f"Enrolled {student.username} in {b1}")

if len(students) > 0:
    e, created = Enrollment.objects.get_or_create(student=students[0], batch=b2, defaults={'status': 'active'})
    if created:
        print(f"Enrolled {students[0].username} in {b2}")

# 7. Create attendance sessions and mark students
today = datetime.date.today()
session1, _ = AttendanceSession.objects.get_or_create(batch=b1, date=today, defaults={'topic': 'Lecture 1', 'created_by': instructor})
session2, _ = AttendanceSession.objects.get_or_create(batch=b1, date=today - datetime.timedelta(days=3), defaults={'topic': 'Lecture 2', 'created_by': instructor})

enrolled_in_b1 = Enrollment.objects.filter(batch=b1, status='active').select_related('student')
for i, e in enumerate(enrolled_in_b1):
    AttendanceRecord.objects.get_or_create(session=session1, student=e.student, defaults={'status': 'present'})
    AttendanceRecord.objects.get_or_create(session=session2, student=e.student, defaults={'status': 'present' if i == 0 else 'absent'})

# 8. Mark first student's enrollment as completed so we can test certificates
if students:
    completed_enroll = Enrollment.objects.filter(student=students[0], batch=b1).first()
    if completed_enroll:
        completed_enroll.status = 'completed'
        completed_enroll.grade = 'A'
        completed_enroll.save()
        print(f"Marked {students[0].username}'s enrollment in {b1} as completed with grade A")

print("\n=== FINAL STATE ===")
print(f"Users: {CustomUser.objects.count()} (admins={CustomUser.objects.filter(role='admin').count()}, instructors={CustomUser.objects.filter(role='instructor').count()}, students={CustomUser.objects.filter(role='student').count()})")
print(f"Courses: {Course.objects.count()}")
print(f"Batches: {Batch.objects.count()}")
print(f"Enrollments: {Enrollment.objects.count()} (active={Enrollment.objects.filter(status='active').count()}, completed={Enrollment.objects.filter(status='completed').count()})")
print(f"Attendance Sessions: {AttendanceSession.objects.count()}")
print(f"Attendance Records: {AttendanceRecord.objects.count()}")
print("\nAll users:")
for u in CustomUser.objects.all():
    print(f"  {u.username} | {u.role} | superuser={u.is_superuser}")
print("\nAll enrollments:")
for e in Enrollment.objects.all():
    print(f"  {e.student.username} -> {e.batch} | status={e.status}")
