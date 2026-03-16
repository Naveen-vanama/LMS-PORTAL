from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    path('course/<int:course_pk>/', views.resource_list, name='list'),
    path('course/<int:course_pk>/upload/', views.resource_upload, name='upload'),
    path('<int:pk>/delete/', views.resource_delete, name='delete'),
    path('<int:pk>/edit/', views.resource_edit, name='edit'),
    path('<int:pk>/track/', views.resource_view_track, name='view_track'),
    path('<int:pk>/logs/', views.resource_views_log, name='views_log'),
    path('<int:pk>/play/', views.resource_play, name='play'),
    path('<int:pk>/stream/', views.serve_video, name='stream'),
]
