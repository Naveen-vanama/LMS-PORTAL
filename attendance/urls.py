from django.urls import path
from . import views

app_name = 'attendance'

urlpatterns = [
    path('batch/<int:batch_pk>/', views.session_list, name='sessions'),
    path('batch/<int:batch_pk>/take/', views.take_attendance, name='take'),
    path('batch/<int:batch_pk>/report/', views.student_report, name='report'),
    path('summary/', views.my_attendance_summary, name='summary'),
    path('manage/', views.manage_attendance_list, name='manage'),
]
