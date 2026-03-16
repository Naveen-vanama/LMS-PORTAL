import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from assignments.models import Assignment, AssignmentSubmission
from assignments.grading_service import AssignmentGradingService
from django.contrib.auth import get_user_model
from django.utils import timezone
User = get_user_model()

# Get first coding assignment and a student
assignment = Assignment.objects.filter(assignment_type='coding').first()
student = User.objects.filter(role='student').first()

print('Testing AI grading...')
print('Assignment:', assignment.title)
print('Student:', student.username)
print()

# Create a mock submission object (not saved)
class FakeSubmission:
    code_submission = '''def reverse_string(s):
    if not s:
        return s
    return s[::-1]
'''
    answer_text = None

submission = FakeSubmission()

try:
    grader = AssignmentGradingService()
    result = grader.grade_submission(assignment, submission)
    print('=== AI GRADING RESULT ===')
    print('Score:', result.get('score'))
    print()
    print('Feedback:', result.get('feedback', '')[:300])
    print()
    print('Suggestions:', result.get('suggestions', '')[:200])
    print()
    print('Reference Solution:', result.get('correct_solution', '')[:200])
    print()
    print('GRADING SUCCESS!')
except Exception as e:
    print('GRADING ERROR:', e)
