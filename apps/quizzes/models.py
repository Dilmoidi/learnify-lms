from django.db import models

class Quiz(models.Model):
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    pass_percentage = models.PositiveIntegerField(default=50, help_text="Percentage needed to pass the quiz (e.g. 50)")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Quizzes"

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    
    OPTION_CHOICES = (
        (1, 'Option 1'),
        (2, 'Option 2'),
        (3, 'Option 3'),
        (4, 'Option 4'),
    )
    correct_option = models.IntegerField(choices=OPTION_CHOICES, help_text="Select the correct option number (1-4)")

    def __str__(self):
        return f"Question in {self.quiz.title}: {self.question_text[:50]}"


class Result(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='quiz_results')
    score = models.PositiveIntegerField()
    total_questions = models.PositiveIntegerField()
    passed = models.BooleanField()
    completed_at = models.DateTimeField(auto_now_add=True)

    @property
    def percentage(self):
        if self.total_questions > 0:
            return int((self.score / self.total_questions) * 100)
        return 0

    def __str__(self):
        return f"{self.student.user.username} - {self.quiz.title}: {self.score}/{self.total_questions} ({'Passed' if self.passed else 'Failed'})"
