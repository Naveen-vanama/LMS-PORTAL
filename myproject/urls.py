"""URL configuration for myproject."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda request: redirect('users:dashboard'), name='home'),
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('users/', include('users.urls', namespace='users')),
    path('courses/', include('courses.urls', namespace='courses')),
    path('enrollments/', include('enrollments.urls', namespace='enrollments')),
    path('resources/', include('resources.urls', namespace='resources')),
    path('attendance/', include('attendance.urls', namespace='attendance')),
    path('certificates/', include('certificates.urls', namespace='certificates')),
    path('payments/', include('payments.urls', namespace='payments')),
    path('api/ai-assistant/', include('ai_assistant.urls', namespace='ai_assistant')),
    path('quizzes/', include('quizzes.urls', namespace='quizzes')),
    path('live-classes/', include('live_classes.urls', namespace='live_classes')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('analytics/', include('analytics.urls', namespace='analytics')),
    path('assignments/', include('assignments.urls', namespace='assignments')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
