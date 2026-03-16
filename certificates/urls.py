from django.urls import path
from . import views

app_name = 'certificates'

urlpatterns = [
    # Instructor action: Check eligibility and issue a certificate
    path('issue/<int:enrollment_id>/', views.check_and_issue_certificate, name='issue_certificate'),
    
    # Student action: Download an issued certificate by its ID
    path('download/<str:certificate_id>/', views.download_certificate, name='download_certificate'),
    
    # List all issued certificates
    path('list/', views.certificate_list, name='list'),
    
    # Public verification page
    path('verify/<uuid:certificate_id>/', views.verify_certificate, name='verify_certificate'),
]
