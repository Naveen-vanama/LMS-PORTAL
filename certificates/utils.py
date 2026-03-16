import io
import qrcode
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from django.utils import timezone


def issue_certificate(enrollment):
    """
    Checks eligibility (>= 75% progress) and issues/retrieves a certificate.
    Returns: (certificate, created, error_message)
    """
    from .models import Certificate

    progress = enrollment.progress
    if progress < 75:
        return None, False, f'Incomplete: {progress}% progress (minimum 75% required).'

    cert, created = Certificate.objects.get_or_create(
        enrollment=enrollment,
        defaults={
            'student': enrollment.student,
            'course': enrollment.batch.course,
            'completion_percentage': progress,
        }
    )
    return cert, created, None


def generate_certificate_pdf(certificate):
    """
    Generates a Coursera/NPTEL-quality professional PDF certificate in memory.

    Features:
    - Luxury dual border (navy + gold)
    - Header banner with platform name
    - Centered title, large student name, accent course name
    - Issue date + Instructor signature placeholder
    - QR code (bottom-right) for public verification
    - Certificate ID + Issued Date in footer
    """
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)

    # ─────────────────────────────────────────────
    # BRANDING CONFIG — update DOMAIN for production
    # ─────────────────────────────────────────────
    PLATFORM_NAME = "Naveen LMS"
    DOMAIN = "https://yourdomain.com"

    # ── Color Palette ──
    PRIMARY   = colors.HexColor('#1e1b4b')   # Deep navy
    GOLD      = colors.HexColor('#c8a84b')   # Rich gold
    ACCENT    = colors.HexColor('#4f46e5')   # Indigo
    LIGHT_BG  = colors.HexColor('#f8f7ff')   # Off-white
    GREY_TEXT = colors.HexColor('#6b7280')
    WHITE     = colors.white

    # ── Background ──
    p.setFillColor(LIGHT_BG)
    p.rect(0, 0, width, height, fill=1, stroke=0)

    # ── Outer border (thick navy) ──
    p.setLineWidth(12)
    p.setStrokeColor(PRIMARY)
    p.rect(18, 18, width - 36, height - 36, stroke=1, fill=0)

    # ── Inner border (thin gold) ──
    p.setLineWidth(2.5)
    p.setStrokeColor(GOLD)
    p.rect(28, 28, width - 56, height - 56, stroke=1, fill=0)

    # ── Corner ornament squares ──
    corner_size = 12
    p.setFillColor(GOLD)
    for cx, cy in [(18, 18), (width-30, 18), (18, height-30), (width-30, height-30)]:
        p.rect(cx, cy, corner_size, corner_size, fill=1, stroke=0)

    # ─────────────────────────────────────────────
    # HEADER BANNER
    # ─────────────────────────────────────────────
    banner_y = height - 68
    p.setFillColor(PRIMARY)
    p.rect(width/2 - 180, banner_y, 360, 44, fill=1, stroke=0)

    # Gold accent lines on banner
    p.setFillColor(GOLD)
    p.rect(width/2 - 180, banner_y, 360, 3, fill=1, stroke=0)
    p.rect(width/2 - 180, banner_y + 41, 360, 3, fill=1, stroke=0)

    # Platform name in banner
    p.setFillColor(WHITE)
    p.setFont("Helvetica-Bold", 15)
    p.drawCentredString(width / 2, banner_y + 15, PLATFORM_NAME.upper())

    # ─────────────────────────────────────────────
    # CERTIFICATE TITLE
    # ─────────────────────────────────────────────
    title_y = height - 145
    p.setFillColor(PRIMARY)
    p.setFont("Helvetica-Bold", 38)
    p.drawCentredString(width / 2, title_y, "CERTIFICATE OF COMPLETION")

    # Gold underline below title
    p.setStrokeColor(GOLD)
    p.setLineWidth(1.5)
    p.line(width/2 - 220, title_y - 6, width/2 + 220, title_y - 6)

    # ─────────────────────────────────────────────
    # BODY: "This is to certify that"
    # ─────────────────────────────────────────────
    p.setFillColor(GREY_TEXT)
    p.setFont("Times-Italic", 16)
    p.drawCentredString(width / 2, height - 195, "This is to certify that")

    # ─────────────────────────────────────────────
    # STUDENT NAME (LARGE)
    # ─────────────────────────────────────────────
    student_name = (certificate.student.get_full_name() or certificate.student.username).upper()
    p.setFillColor(PRIMARY)
    p.setFont("Helvetica-Bold", 38)
    p.drawCentredString(width / 2, height - 248, student_name)

    # Decorative name underline
    name_width = min(len(student_name) * 17, 500)
    p.setStrokeColor(GOLD)
    p.setLineWidth(1)
    p.line(width/2 - name_width//2, height - 258, width/2 + name_width//2, height - 258)

    # ─────────────────────────────────────────────
    # COMPLETION TEXT
    # ─────────────────────────────────────────────
    p.setFillColor(GREY_TEXT)
    p.setFont("Helvetica", 14)
    p.drawCentredString(
        width / 2, height - 295,
        f"has successfully completed {int(certificate.completion_percentage)}% of"
    )

    # ─────────────────────────────────────────────
    # COURSE NAME
    # ─────────────────────────────────────────────
    p.setFillColor(ACCENT)
    p.setFont("Helvetica-Bold", 26)
    p.drawCentredString(width / 2, height - 335, certificate.course.title)

    # ─────────────────────────────────────────────
    # ISSUE DATE (centered)
    # ─────────────────────────────────────────────
    issued_str = certificate.issued_date.strftime('%B %d, %Y')
    p.setFillColor(GREY_TEXT)
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, height - 368, f"Issued on: {issued_str}")

    # ─────────────────────────────────────────────
    # SIGNATURE SECTION
    # ─────────────────────────────────────────────
    sig_y = 148
    sig_line_len = 160

    # Left signature — Director
    lx = 130
    p.setStrokeColor(PRIMARY)
    p.setLineWidth(1)
    p.line(lx - sig_line_len//2, sig_y, lx + sig_line_len//2, sig_y)
    p.setFillColor(PRIMARY)
    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(lx, sig_y - 12, "DIRECTOR")
    p.setFillColor(GREY_TEXT)
    p.setFont("Helvetica", 8)
    p.drawCentredString(lx, sig_y - 23, PLATFORM_NAME)

    # Right signature — Instructor
    rx = width - 130
    instructor_name = (
        certificate.course.instructor.get_full_name()
        or certificate.course.instructor.username
    ).upper()
    p.setStrokeColor(PRIMARY)
    p.line(rx - sig_line_len//2, sig_y, rx + sig_line_len//2, sig_y)
    p.setFillColor(PRIMARY)
    p.setFont("Helvetica-Bold", 9)
    p.drawCentredString(rx, sig_y - 12, instructor_name)
    p.setFillColor(GREY_TEXT)
    p.setFont("Helvetica", 8)
    p.drawCentredString(rx, sig_y - 23, "COURSE INSTRUCTOR")

    # ─────────────────────────────────────────────
    # QR CODE (bottom-right)
    # ─────────────────────────────────────────────
    verify_url = f"{DOMAIN}/certificates/verify/{certificate.id}/"
    qr = qrcode.QRCode(version=1, box_size=7, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#1e1b4b", back_color="white")

    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    qr_size = 80
    qr_x = width - 50 - qr_size
    qr_y = 48
    p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, qr_size, qr_size)
    p.setFont("Helvetica", 7)
    p.setFillColor(GREY_TEXT)
    p.drawCentredString(qr_x + qr_size / 2, qr_y - 9, "SCAN TO VERIFY")

    # ─────────────────────────────────────────────
    # FOOTER: Certificate ID + Issued Date
    # ─────────────────────────────────────────────
    footer_y = 50
    p.setFont("Helvetica", 8)
    p.setFillColor(GREY_TEXT)
    p.drawString(45, footer_y, f"Certificate ID:  {certificate.certificate_id}")
    p.drawString(45, footer_y - 12, f"Issued:  {issued_str}")
    p.drawString(45, footer_y - 24, f"Verify:  {verify_url}")

    p.showPage()
    p.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
