from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    path('course/<int:course_id>/', views.quiz_list, name='list'),
    path('generate/<int:course_id>/', views.generate_quiz, name='generate'),
    path('<int:quiz_id>/take/', views.take_quiz, name='take'),
    path('<int:quiz_id>/results/', views.quiz_results, name='results'),
    path('course/<int:course_id>/daily/', views.start_daily_quiz, name='start_daily'),
    path('course/<int:course_id>/toggle-revision/', views.toggle_auto_revision, name='toggle_revision'),
    path('course/<int:course_id>/manual-revision/', views.manual_trigger_revision, name='manual_revision'),
    path('revision/<int:quiz_id>/edit/', views.edit_revision, name='edit_revision'),
]
