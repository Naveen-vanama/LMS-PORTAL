from django.contrib import admin
from .models import Certificate

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('certificate_id', 'get_student', 'get_course', 'issued_date')
    search_fields = ('certificate_id', 'enrollment__student__username', 'enrollment__student__first_name', 'enrollment__student__last_name')
    list_filter = ('issued_date', 'enrollment__batch__course')

    def get_student(self, obj):
        return obj.enrollment.student.get_full_name() or obj.enrollment.student.username
    get_student.short_description = 'Student'

    def get_course(self, obj):
        return obj.enrollment.batch.course.title
    get_course.short_description = 'Course'
