import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from courses.models import Batch
from enrollments.models import Enrollment

def fix_jayanth():
    print("--- Fixing Jayanth's Enrollment ---")
    j = CustomUser.objects.filter(username='jayanth').first()
    if not j:
        print("User jayanth not found. Creating...")
        j = CustomUser.objects.create_user(username='jayanth', password='password123', email='jayanth@example.com', role='student')
    
    # Ensure role is student
    if j.role != 'student':
        j.role = 'student'
        j.save()
        print("Updated jayanth's role to student.")

    # Get first batch
    batch = Batch.objects.first()
    if not batch:
        print("No batches found to enroll jayanth in.")
        return

    # Enroll
    e, created = Enrollment.objects.get_or_create(
        student=j, 
        batch=batch,
        defaults={'status': 'active'}
    )
    
    if not created:
        if e.status != 'active':
            e.status = 'active'
            e.save()
            print(f"Updated jayanth's enrollment in {batch} to ACTIVE.")
        else:
            print(f"jayanth is already active in {batch}.")
    else:
        print(f"Successfully enrolled jayanth in {batch}.")

    # Let's also check another common student name or just ensure general sanity
    alice = CustomUser.objects.filter(username='alice').first()
    if alice and not Enrollment.objects.filter(student=alice).exists():
        Enrollment.objects.get_or_create(student=alice, batch=batch, defaults={'status': 'active'})
        print(f"Enrolled alice in {batch}.")

if __name__ == "__main__":
    fix_jayanth()
