from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # Student
    path('course/<int:course_id>/', views.assignment_list, name='list'),
    path('<int:pk>/', views.assignment_detail, name='detail'),
    path('<int:pk>/submit/', views.submit_assignment, name='submit'),
    path('<int:pk>/result/', views.assignment_result, name='result'),
    path('my/', views.student_assignment_dashboard, name='student_dashboard'),

    # Instructor
    path('manage/', views.instructor_dashboard, name='instructor_dashboard'),
    path('create/', views.create_assignment, name='create'),
    path('<int:assignment_id>/submissions/', views.instructor_submissions, name='instructor_submissions'),
    path('review/<int:submission_id>/', views.instructor_review, name='review'),
]
