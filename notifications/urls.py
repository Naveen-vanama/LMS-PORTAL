from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('mark-read/<int:pk>/', views.mark_as_read, name='mark_read'),
    path('api/', views.api_notifications, name='api_list'),
]
