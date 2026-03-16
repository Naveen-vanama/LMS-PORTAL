import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from users.models import CustomUser
from enrollments.models import Enrollment

print("Username      | Role       | Enrollments")
print("---------------------------------------")
for u in CustomUser.objects.all().order_by('username'):
    count = Enrollment.objects.filter(student=u).count()
    print(f"{u.username:13} | {u.role:10} | {count}")
