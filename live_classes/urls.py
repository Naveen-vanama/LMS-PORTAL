from django.urls import path
from . import views

app_name = 'live_classes'

urlpatterns = [
    path('course/<int:course_id>/', views.live_class_list, name='list'),
    path('course/<int:course_id>/schedule/', views.schedule_class, name='schedule'),
    path('join/<int:class_id>/', views.join_class, name='join'),
    path('end/<int:class_id>/', views.end_class, name='end'),
    path('upload-recording/<int:class_id>/', views.upload_recording, name='upload_recording'),
    path('attendance/<int:class_id>/', views.view_attendance, name='attendance'),
]
