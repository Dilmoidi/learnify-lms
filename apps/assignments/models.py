from django.db import models

class Assignment(models.Model):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateTimeField()
    max_marks = models.PositiveIntegerField(default=100)
    attachment = models.FileField(upload_to='assignments/files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def pending_submissions_count(self):
        return self.submissions.filter(status='submitted').count()

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='submissions')
    submitted_file = models.FileField(upload_to='assignments/submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.PositiveIntegerField(blank=True, null=True)
    feedback = models.TextField(blank=True)
    
    STATUS_CHOICES = (
        ('submitted', 'Submitted'),
        ('graded', 'Graded'),
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='submitted')

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"Submission: {self.student.user.username} for {self.assignment.title}"
