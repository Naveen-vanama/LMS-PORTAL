from django.db import models
from django.conf import settings
from courses.models import Course, Lesson

class Assignment(models.Model):
    ASSIGNMENT_TYPES = [
        ('coding', 'Coding'),
        ('text', 'Text'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    batch = models.ForeignKey(
        'courses.Batch', on_delete=models.CASCADE, related_name='assignments',
        null=True, blank=True,
        help_text='Leave blank to make available to all batches of this course.'
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assignment_type = models.CharField(max_length=10, choices=ASSIGNMENT_TYPES, default='text')
    max_score = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AssignmentSubmission(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='assignment_submissions'
    )
    assignment = models.ForeignKey(
        Assignment, 
        on_delete=models.CASCADE, 
        related_name='submissions'
    )
    answer_text = models.TextField(blank=True, null=True)
    code_submission = models.TextField(blank=True, null=True)
    
    # AI Grading
    ai_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ai_feedback = models.TextField(blank=True, null=True)
    
    # Instructor Review
    manual_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    manual_feedback = models.TextField(blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"

    @property
    def final_score(self):
        return self.manual_score if self.manual_score is not None else self.ai_score

    @property
    def final_feedback(self):
        return self.manual_feedback if self.manual_feedback else self.ai_feedback
