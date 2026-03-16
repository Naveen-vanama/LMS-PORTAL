from django.contrib import admin
from .models import Assignment, AssignmentSubmission

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display  = ('title', 'course', 'lesson', 'assignment_type', 'max_score', 'created_at')
    list_filter   = ('assignment_type', 'course')
    search_fields = ('title', 'course__title')

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    list_display  = ('student', 'assignment', 'ai_score', 'manual_score', 'submitted_at', 'graded_at')
    list_filter   = ('assignment__course',)
    search_fields = ('student__username', 'assignment__title')
    readonly_fields = ('submitted_at', 'graded_at', 'ai_score', 'ai_feedback')
