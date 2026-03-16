from django.contrib import admin
from .models import Course, Batch, Group, Announcement


class BatchInline(admin.TabularInline):
    model = Batch
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'instructor', 'status', 'credits', 'created_at')
    list_filter = ('status', 'credits')
    search_fields = ('title', 'code', 'instructor__username')
    inlines = [BatchInline]


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'start_date', 'end_date', 'max_students', 'enrolled_count')
    list_filter = ('course',)
    search_fields = ('name', 'course__title')

    @admin.display(description='Enrolled')
    def enrolled_count(self, obj):
        return obj.enrollments.count()


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch')
    filter_horizontal = ('members',)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'batch', 'author', 'created_at')
    list_filter = ('course', 'batch')
    search_fields = ('title', 'content')
