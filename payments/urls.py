from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('list/', views.payment_list, name='list'),
    path('checkout/<int:enrollment_pk>/', views.checkout, name='checkout'),
    path('create-order/<int:enrollment_pk>/', views.create_razorpay_order, name='create_order'),
    path('process/<int:enrollment_pk>/', views.process_payment, name='process'),
    path('status/<int:payment_pk>/', views.payment_status, name='status'),
    path('receipt/<int:payment_pk>/', views.download_receipt, name='download_receipt'),
    path('manual-verify/<int:enrollment_pk>/', views.manual_payment_verify, name='manual_verify'),
]
