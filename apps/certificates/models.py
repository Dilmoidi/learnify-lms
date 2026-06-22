import uuid
from django.db import models

class Certificate(models.Model):
    enrollment = models.OneToOneField('courses.Enrollment', on_delete=models.CASCADE, related_name='certificate')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='certificates')
    issued_at = models.DateTimeField(auto_now_add=True)
    certificate_uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return f"Certificate: {self.student.user.username} - {self.course.title}"
