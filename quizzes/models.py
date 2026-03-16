from django.db import models
from django.conf import settings
from courses.models import Course, Lesson

class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    is_daily = models.BooleanField(default=False)
    is_revision = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Question(models.Model):
    class Type(models.TextChoices):
        MCQ = 'mcq', 'Multiple Choice'
        SHORT_ANSWER = 'short_answer', 'Short Answer'
        TRUE_FALSE = 'true_false', 'True / False'

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=Type.choices, default=Type.MCQ)
    options = models.JSONField(blank=True, null=True, help_text="List of options for MCQ/TF")
    correct_answer = models.TextField()
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.get_question_type_display()}: {self.question_text[:50]}"

class StudentAnswer(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers')
    selected_answer = models.TextField()
    is_correct = models.BooleanField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'question')


class DailyQuiz(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_quizzes')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name='daily_assignment')
    topic_name = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Daily Quiz for {self.student.username} - {self.topic_name}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class RevisionQuiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='revision_quizzes')
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name='revision_assignment')
    title = models.CharField(max_length=255, default="Revision Quiz")
    topics_covered = models.TextField(help_text="Comma separated list of topics")
    date_generated = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Revision Quiz for {self.course.title} - {self.date_generated}"


class StudentStreak(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_quiz_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.username}: {self.current_streak} days"


class StudentBadge(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='badges')
    badge_name = models.CharField(max_length=100)
    earned_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} earned {self.badge_name}"
