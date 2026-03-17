from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('', views.course_list, name='list'),
    path('<int:pk>/', views.course_detail, name='detail'),
    path('create/', views.course_create, name='create'),
    path('<int:pk>/edit/', views.course_edit, name='edit'),
    path('<int:course_pk>/batch/create/', views.batch_create, name='batch_create'),
    path('batch/<int:batch_pk>/group/create/', views.group_create, name='group_create'),
    path('<int:course_pk>/announcement/create/', views.announcement_create, name='announcement_create'),
    path('<int:course_id>/ai-generator/', views.course_generator, name='course_generator'),
    path('<int:course_id>/generator-preview/', views.generator_preview, name='generator_preview'),
    path('announcement/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
]
