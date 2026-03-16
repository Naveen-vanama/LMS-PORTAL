from django.contrib import admin
from .models import LiveClass, LiveClassAttendance, LiveChatMessage

@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'instructor', 'scheduled_time', 'is_active')
    list_filter = ('course', 'instructor', 'is_active')
    search_fields = ('title', 'description')

@admin.register(LiveClassAttendance)
class LiveClassAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'live_class', 'join_time', 'leave_time', 'duration')
    list_filter = ('live_class', 'student')

@admin.register(LiveChatMessage)
class LiveChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'live_class', 'timestamp')
    list_filter = ('live_class', 'user')
