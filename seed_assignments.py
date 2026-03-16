import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from assignments.models import Assignment, AssignmentSubmission
from courses.models import Course, Lesson
from django.contrib.auth import get_user_model
User = get_user_model()

course = Course.objects.first()
lesson = Lesson.objects.first()
print('Using course:', course)
print('Using lesson:', lesson)

# Create coding assignment
a = Assignment.objects.filter(title='Python String Reversal Challenge').first()
if not a:
    a = Assignment.objects.create(
        title='Python String Reversal Challenge',
        course=course,
        lesson=lesson,
        description='Write a Python function called reverse_string that takes a string s and returns the reversed string. Handle edge cases like empty strings.',
        assignment_type='coding',
        max_score=10,
    )
    print('Assignment CREATED: [' + str(a.pk) + '] ' + a.title)
else:
    print('Assignment already exists: [' + str(a.pk) + '] ' + a.title)

# Create text assignment too
b = Assignment.objects.filter(title='Explain Python Slicing').first()
if not b:
    b = Assignment.objects.create(
        title='Explain Python Slicing',
        course=course,
        lesson=lesson,
        description='Explain how Python list/string slicing works. Include examples with step parameter. Explain time complexity.',
        assignment_type='text',
        max_score=10,
    )
    print('Assignment CREATED: [' + str(b.pk) + '] ' + b.title)
else:
    print('Assignment already exists: [' + str(b.pk) + '] ' + b.title)

print()
print('=== KEY URLS ===')
print('Assignment List (student): http://127.0.0.1:8000/assignments/course/' + str(course.pk) + '/')
print('Assignment Detail:         http://127.0.0.1:8000/assignments/' + str(a.pk) + '/')
print('Instructor Dashboard:      http://127.0.0.1:8000/assignments/manage/')
print('Student Dashboard:         http://127.0.0.1:8000/assignments/my/')
print('Create Assignment:         http://127.0.0.1:8000/assignments/create/')
print('Admin:                     http://127.0.0.1:8000/admin/assignments/')
