from django.urls import path
from . import views

app_name = 'enrollments'

urlpatterns = [
    path('', views.enrollment_list, name='list'),
    path('enroll/<int:batch_pk>/', views.enroll, name='enroll'),
    path('unenroll/<int:batch_pk>/', views.unenroll, name='unenroll'),
    path('<int:pk>/grade/', views.grade_update, name='grade_update'),
    path('<int:pk>/complete/', views.mark_complete, name='mark_complete'),
]
