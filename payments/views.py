from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Payment
from enrollments.models import Enrollment
from django.db.models import Q
from django.http import HttpResponse
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
import razorpay
from django.conf import settings

try:
    client = razorpay.Client(auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
except Exception as e:
    client = None
    print(f"Razorpay Client Init Error: {e}")

@login_required
def payment_list(request):
    """List payments for students (their own) or admins (all)."""
    if request.user.is_student:
        payments = Payment.objects.filter(enrollment__student=request.user)
    else:
        # Admins and Instructors can see all relevant payments
        payments = Payment.objects.all()

    query = request.GET.get('q', '')
    if query:
        payments = payments.filter(
            Q(transaction_id__icontains=query) |
            Q(enrollment__student__username__icontains=query) |
            Q(enrollment__batch__course__title__icontains=query)
        )

    return render(request, 'payments/payment_list.html', {
        'payments': payments,
        'query': query
    })

@login_required
def checkout(request, enrollment_pk):
    """Prepare a payment for an enrollment, supporting partial payments."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user)
    
    # Check if already fully paid
    if enrollment.is_paid:
        messages.info(request, 'You have already fully paid for this course.')
        return redirect('enrollments:list')

    # Suggested amount is the remaining balance
    balance = enrollment.balance_due
    
    if balance <= 0:
        messages.success(request, 'No balance due!')
        return redirect('enrollments:list')

    return render(request, 'payments/checkout.html', {
        'enrollment': enrollment,
        'balance': balance,
        'razorpay_key_id': settings.RAZOR_KEY_ID,
    })

@login_required
def create_razorpay_order(request, enrollment_pk):
    """AJAX view to create a Razorpay order on the fly based on user-entered amount."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user)
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            amount = float(data.get('amount', 0))
        except (ValueError, json.JSONDecodeError):
            return HttpResponse(status=400)

        if amount <= 0 or amount > float(enrollment.balance_due):
            return HttpResponse(status=400)

        if not client:
            return HttpResponse(json.dumps({'error': 'Razorpay not configured. Admin must update Secret Key.'}), status=500, content_type="application/json")

        # Create Order (amount in paise)
        order_data = {
            'amount': int(amount * 100),
            'currency': 'INR',
            'payment_capture': 1  # Auto capture
        }
        try:
            order = client.order.create(data=order_data)
            return HttpResponse(json.dumps({'order_id': order['id']}), content_type="application/json")
        except razorpay.errors.BadRequestError as e:
            return HttpResponse(json.dumps({'error': f'Razorpay Auth Failed: {str(e)}. Check your Secret Key.'}), status=401, content_type="application/json")
        except Exception as e:
            return HttpResponse(json.dumps({'error': f'Razorpay Error: {str(e)}'}), status=500, content_type="application/json")
    return HttpResponse(status=405)

@login_required
def process_payment(request, enrollment_pk):
    """Verify Razorpay payment signature."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user)
    
    if request.method == 'POST':
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        amount = float(request.POST.get('amount', 0))

        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            # Verify the signature
            client.utility.verify_payment_signature(params_dict)
            
            # Payment is verified, update records
            payment = Payment.objects.create(
                enrollment=enrollment,
                amount=amount,
                transaction_id=razorpay_payment_id,
                status=Payment.Status.COMPLETED,
                paid_at=timezone.now(),
                payment_method=Payment.PaymentMethod.UPI
            )
            
            if enrollment.status == Enrollment.Status.PENDING_PAYMENT:
                enrollment.status = Enrollment.Status.PENDING_APPROVAL
                enrollment.save()
            
            from notifications.services import notify_user
            notify_user(
                user=enrollment.student,
                title="Payment Successful",
                message=f"Your payment of ₹{amount} for {enrollment.batch.course.code} has been successfully processed.",
                n_type='PAYMENT_SUCCESS',
                link=reverse('payments:status', kwargs={'payment_pk': payment.pk}),
                send_email=True
            )
            
            messages.success(request, f'Payment of ₹{amount} verified via Razorpay!')
            return redirect('payments:status', payment_pk=payment.pk)

        except razorpay.errors.SignatureVerificationError:
            messages.error(request, 'Payment verification failed.')
            return redirect('payments:checkout', enrollment_pk=enrollment.pk)
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('payments:checkout', enrollment_pk=enrollment.pk)

    return redirect('payments:checkout', enrollment_pk=enrollment.pk)

@login_required
def payment_status(request, payment_pk):
    """View payment status details."""
    payment = get_object_or_404(Payment, pk=payment_pk)
    
    # Permission check: student can only see their own
    if request.user.is_student and payment.enrollment.student != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')

    return render(request, 'payments/payment_status.html', {
        'payment': payment
    })

@login_required
def download_receipt(request, payment_pk):
    """Generate a PDF receipt for a completed payment."""
    payment = get_object_or_404(Payment, pk=payment_pk)
    
    # Permission check
    if request.user.is_student and payment.enrollment.student != request.user:
        messages.error(request, 'Permission denied.')
        return redirect('users:dashboard')
    
    if payment.status != Payment.Status.COMPLETED:
        messages.error(request, 'Receipt is only available for completed payments.')
        return redirect('payments:status', payment_pk=payment.pk)

    # Create byte stream
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Header
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width/2.0, height - 1*inch, "COLLEGE PORTAL")
    
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2.0, height - 1.3*inch, "Official Payment Receipt")
    
    p.line(1*inch, height - 1.5*inch, width - 1*inch, height - 1.5*inch)

    # Body
    text_y = height - 2*inch
    p.setFont("Helvetica-Bold", 14)
    p.drawString(1*inch, text_y, "Transaction Details")
    
    p.setFont("Helvetica", 12)
    details = [
        ("Transaction ID:", payment.transaction_id),
        ("Student Name:", payment.enrollment.student.get_full_name() or payment.enrollment.student.username),
        ("Course Name:", payment.enrollment.batch.course.title),
        ("Batch:", payment.enrollment.batch.name),
        ("Total Course Fee:", f"INR {payment.enrollment.batch.course.price}"),
        ("This Payment:", f"INR {payment.amount}"),
        ("Total Amount Paid:", f"INR {payment.enrollment.total_paid}"),
        ("Remaining Balance:", f"INR {payment.enrollment.balance_due}"),
        ("Payment Method:", payment.get_payment_method_display()),
        ("Payment Date:", payment.paid_at.strftime("%B %d, Y %H:%M:%S") if payment.paid_at else "N/A"),
        ("Status:", payment.status.upper()),
    ]
    
    text_y -= 0.4*inch
    for label, value in details:
        p.setFont("Helvetica-Bold", 11)
        p.drawString(1.2*inch, text_y, label)
        p.setFont("Helvetica", 11)
        p.drawString(2.8*inch, text_y, str(value))
        text_y -= 0.3*inch

    # Footer
    p.line(1*inch, 2*inch, width - 1*inch, 2*inch)
    p.setFont("Helvetica-Oblique", 10)
    p.drawCentredString(width/2.0, 1.7*inch, "This is a computer-generated receipt and does not require a physical signature.")
    p.drawCentredString(width/2.0, 1.5*inch, f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Finalize
    p.showPage()
    p.save()

    buffer.seek(0)
    return HttpResponse(buffer, content_type='application/pdf', 
                        headers={'Content-Disposition': f'attachment; filename="Receipt_{payment.transaction_id}.pdf"'})

@login_required
def manual_payment_verify(request, enrollment_pk):
    """Fallback view for testing without active Razorpay keys."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_pk, student=request.user)
    if request.method == 'POST':
        amount = float(request.POST.get('amount', 0))
        payment = Payment.objects.create(
            enrollment=enrollment,
            amount=amount,
            status=Payment.Status.COMPLETED,
            paid_at=timezone.now(),
            payment_method=Payment.PaymentMethod.UPI,
            transaction_id=f"MANUAL-{timezone.now().timestamp()}"
        )
        if enrollment.status == Enrollment.Status.PENDING_PAYMENT:
            enrollment.status = Enrollment.Status.PENDING_APPROVAL
            enrollment.save()
        from notifications.services import notify_user
        notify_user(
            user=enrollment.student,
            title="Payment Successful (Simulated)",
            message=f"Your simulated payment of ₹{amount} for {enrollment.batch.course.code} has been successfully processed.",
            n_type='PAYMENT_SUCCESS',
            link=reverse('payments:status', kwargs={'payment_pk': payment.pk}),
            send_email=True
        )
        
        messages.success(request, f'Simulated Payment of ₹{amount} successful!')
        return redirect('payments:status', payment_pk=payment.pk)
    return redirect('payments:checkout', enrollment_pk=enrollment.pk)
