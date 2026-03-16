from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    path('student/', views.student_analytics_dashboard, name='student_dashboard'),
    path('course/<int:course_id>/', views.instructor_analytics_dashboard, name='instructor_dashboard'),
    
    # API endpoints
    path('api/student/', views.api_student_analytics, name='api_student'),
    path('api/instructor/<int:course_id>/', views.api_instructor_analytics, name='api_instructor'),
]
