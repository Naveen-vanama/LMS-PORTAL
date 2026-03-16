import os
import django
from django.core.files.base import ContentFile
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from django.contrib.auth import get_user_model
from courses.models import Course, Batch
from enrollments.models import Enrollment
from resources.models import FileResource
from attendance.models import AttendanceSession, AttendanceRecord

User = get_user_model()

def create_image(color, text):
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        img = Image.new('RGB', (800, 600), color=color)
        d = ImageDraw.Draw(img)
        d.text((300, 250), text, fill=(255,255,255))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except ImportError:
        return b''

def run():
    print("Clearing old data...")
    User.objects.exclude(username='admin').delete()
    Course.objects.all().delete()
    
    # 1. Users
    print("Creating users...")
    instructor = User.objects.create_user('prof_smith', 'smith@example.com', 'password', first_name='John', last_name='Smith', role='instructor')
    student1 = User.objects.create_user('alice', 'alice@example.com', 'password', first_name='Alice', last_name='Johnson', role='student')
    student2 = User.objects.create_user('bob', 'bob@example.com', 'password', first_name='Bob', last_name='Williams', role='student')
    
    # Optional Profile Pictures
    img_bytes = create_image((50,50,150), 'Prof')
    if img_bytes:
        instructor.profile_picture.save('prof.png', ContentFile(img_bytes))
    
    # 2. Courses
    print("Creating courses...")
    course1 = Course.objects.create(title='Introduction to Programming', code='CS101', description='Learn basic programming in Python.', instructor=instructor)
    course2 = Course.objects.create(title='Data Structures', code='CS201', description='Advanced data structures.', instructor=instructor)

    # Optional Course Thumbnails
    img_bytes1 = create_image((0, 100, 0), 'CS101')
    img_bytes2 = create_image((100, 0, 0), 'CS201')
    if img_bytes1:
        course1.thumbnail.save('cs101.png', ContentFile(img_bytes1))
        course2.thumbnail.save('cs201.png', ContentFile(img_bytes2))
    
    # 3. Batches
    print("Creating batches...")
    b1 = Batch.objects.create(course=course1, name='Fall 2026', start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 12, 15))
    b2 = Batch.objects.create(course=course2, name='Spring 2026', start_date=datetime.date(2026, 1, 15), end_date=datetime.date(2026, 5, 15))
    
    # 4. Enrollments
    print("Enrolling students...")
    Enrollment.objects.create(student=student1, batch=b1, status='active')
    Enrollment.objects.create(student=student2, batch=b1, status='active')
    Enrollment.objects.create(student=student1, batch=b2, status='active')
    
    # 5. Resources
    print("Adding resources...")
    res = FileResource.objects.create(title='Lecture 1 Slides', description='Introductory slides.', resource_type='lecture', course=course1, uploaded_by=instructor)
    res.file.save('lecture1.txt', ContentFile(b'Welcome to CS101!'))
    res2 = FileResource.objects.create(title='Course Syllabus', description='The complete syllabus for CS201.', resource_type='reading', course=course2, uploaded_by=instructor)
    res2.file.save('syllabus.txt', ContentFile(b'Syllabus Content...'))

    # 6. Attendance
    print("Adding attendance...")
    s1 = AttendanceSession.objects.create(batch=b1, date=datetime.date.today(), topic='Intro', created_by=instructor)
    AttendanceRecord.objects.create(session=s1, student=student1, status='present')
    AttendanceRecord.objects.create(session=s1, student=student2, status='absent')
    
    print("Database populated successfully!")

if __name__ == '__main__':
    run()
