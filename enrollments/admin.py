from django.contrib import admin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'batch', 'status', 'grade', 'enrolled_at')
    list_filter = ('status', 'batch__course')
    search_fields = ('student__username', 'batch__course__title')
    list_editable = ('status', 'grade')
