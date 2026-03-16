from django.contrib import admin
from .models import FileResource, ResourceView


@admin.register(FileResource)
class FileResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'batch', 'resource_type', 'uploaded_by', 'is_visible', 'created_at')
    list_filter = ('resource_type', 'is_visible', 'course')
    search_fields = ('title', 'course__title')
    list_editable = ('is_visible',)


@admin.register(ResourceView)
class ResourceViewAdmin(admin.ModelAdmin):
    list_display = ('student', 'resource', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('student__username', 'resource__title')
