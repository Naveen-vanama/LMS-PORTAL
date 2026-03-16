from django.db import models
from django.conf import settings
from courses.models import Course

class CourseContentChunk(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='content_chunks')
    chunk_text = models.TextField()
    embedding = models.JSONField(blank=True, null=True) 
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chunk for {self.course.code}"


class ChatMessage(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_chats')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ai_chats')
    question = models.TextField()
    answer = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Chat: {self.student.username} regarding {self.course.code}"


class AITestLog(models.Model):
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_test_logs')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ai_test_logs')
    question = models.TextField()
    retrieved_chunks = models.JSONField(blank=True, null=True)
    ai_response = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"AI Test: {self.instructor.username} on {self.course.code}"
