from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.urls import reverse

from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from .models import Certificate
from apps.courses.models import Enrollment

# Helper function to check and award certificate
def check_and_award_certificate(enrollment):
    if enrollment.progress_percentage == 100:
        # Check if certificate already awarded
        certificate, created = Certificate.objects.get_or_create(
            enrollment=enrollment,
            student=enrollment.student,
            course=enrollment.course
        )
        return certificate
    return None


# Download Certificate View (PDF Generation)
@login_required
def download_certificate(request, certificate_uuid):
    certificate = get_object_or_404(Certificate, certificate_uuid=certificate_uuid)
    user = request.user
    
    # Authorization: Student owner, Course Instructor, or Admin
    is_owner = (user.role == 'student' and hasattr(user, 'student_profile') and certificate.student == user.student_profile)
    is_instructor = (user.role == 'instructor' and certificate.course.instructor == getattr(user, 'instructor_profile', None))
    
    if not (is_owner or is_instructor or user.is_superuser):
        messages.error(request, "Access denied. You do not have permission to view this certificate.")
        return redirect('dashboard')

    # Initialize PDF Response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate-{certificate.course.slug}.pdf"'

    # Define dimensions (Landscape Letter: 11 x 8.5 inches)
    width, height = landscape(letter)
    p = canvas.Canvas(response, pagesize=landscape(letter))
    
    # 1. Base Dark Theme Background
    p.setFillColor(HexColor('#0e0c1a'))
    p.rect(0, 0, width, height, fill=True, stroke=False)
    
    # 2. Double Line Accent Borders
    p.setStrokeColor(HexColor('#3c3489'))
    p.setLineWidth(3)
    p.rect(20, 20, width - 40, height - 40)
    
    p.setStrokeColor(HexColor('#7f77dd'))
    p.setLineWidth(1)
    p.rect(26, 26, width - 52, height - 52)
    
    # Corner circles
    p.setFillColor(HexColor('#534ab7'))
    p.circle(20, 20, 6, fill=True, stroke=False)
    p.circle(width-20, 20, 6, fill=True, stroke=False)
    p.circle(20, height-20, 6, fill=True, stroke=False)
    p.circle(width-20, height-20, 6, fill=True, stroke=False)
    
    # 3. Logo/Brand
    p.setFillColor(HexColor('#7f77dd'))
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2.0, height - 90, "L E A R N I F Y")
    
    # 4. Heading
    p.setFillColor(HexColor('#eeedfe'))
    p.setFont("Helvetica-Bold", 30)
    p.drawCentredString(width / 2.0, height - 150, "CERTIFICATE OF COMPLETION")
    
    # 5. Presentation Text
    p.setFillColor(HexColor('#cecbf6'))
    p.setFont("Helvetica", 14)
    p.drawCentredString(width / 2.0, height - 200, "This is proudly presented to")
    
    # 6. Student Name
    p.setFillColor(HexColor('#5dcaa5'))
    p.setFont("Helvetica-Bold", 28)
    student_name = certificate.student.user.get_full_name() or certificate.student.user.username
    p.drawCentredString(width / 2.0, height - 250, student_name.upper())
    
    # 7. Subtext
    p.setFillColor(HexColor('#cecbf6'))
    p.setFont("Helvetica", 13)
    p.drawCentredString(width / 2.0, height - 295, "for successfully meeting all criteria and completing the syllabus for")
    
    # 8. Course Title
    p.setFillColor(HexColor('#afa9ec'))
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width / 2.0, height - 340, f'"{certificate.course.title}"')
    
    # 9. Issuance Date
    p.setFillColor(HexColor('#cecbf6'))
    p.setFont("Helvetica", 11)
    issue_date = certificate.issued_at.strftime("%B %d, %Y")
    p.drawCentredString(width / 2.0, height - 380, f"Issued on {issue_date}")
    
    # 10. Signatures
    p.setStrokeColor(HexColor('#26215c'))
    p.setLineWidth(1)
    
    # Instructor Signature Line
    p.line(100, 130, 300, 130)
    p.setFillColor(HexColor('#cecbf6'))
    p.setFont("Helvetica", 9)
    p.drawCentredString(200, 115, "COURSE INSTRUCTOR")
    p.setFillColor(HexColor('#eeedfe'))
    p.setFont("Helvetica-Oblique", 11)
    instr_name = certificate.course.instructor.user.get_full_name() or certificate.course.instructor.user.username
    p.drawCentredString(200, 140, instr_name)
    
    # Auditor Signature Line
    p.line(width - 300, 130, width - 100, 130)
    p.setFillColor(HexColor('#cecbf6'))
    p.setFont("Helvetica", 9)
    p.drawCentredString(width - 200, 115, "LEARNIFY AUDITOR")
    p.setFillColor(HexColor('#eeedfe'))
    p.setFont("Helvetica-Oblique", 11)
    p.drawCentredString(width - 200, 140, "Authorized Audit Board")
    
    # 11. Verification Metadata
    p.setFillColor(HexColor('#534ab7'))
    p.setFont("Helvetica", 7.5)
    verify_url = request.build_absolute_uri(reverse('certificates:verify_certificate', kwargs={'certificate_uuid': certificate.certificate_uuid}))
    p.drawCentredString(width / 2.0, 55, f"Verify authenticity online: {verify_url}")
    p.drawCentredString(width / 2.0, 42, f"Verification ID: {certificate.certificate_uuid}")

    # Build and Save
    p.showPage()
    p.save()
    return response


# Public Verification Landing Page
def verify_certificate(request, certificate_uuid):
    certificate = Certificate.objects.filter(certificate_uuid=certificate_uuid).select_related('student__user', 'course__instructor__user').first()
    
    return render(request, 'certificates/verify_certificate.html', {
        'certificate': certificate,
        'certificate_uuid': certificate_uuid
    })
