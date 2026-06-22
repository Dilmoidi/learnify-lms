from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.courses.models import LessonProgress
from apps.quizzes.models import Result
from apps.assignments.models import Submission

from .utils import update_streak, update_skill_progress, check_and_unlock_badges, recalculate_score

@receiver(post_save, sender=LessonProgress)
def handle_lesson_completed(sender, instance, created, **kwargs):
    if instance.is_completed:
        student = instance.enrollment.student
        update_streak(student)
        update_skill_progress(student, instance.lesson.course)
        check_and_unlock_badges(student)
        recalculate_score(student)

@receiver(post_save, sender=Result)
def handle_quiz_completed(sender, instance, created, **kwargs):
    if created:
        student = instance.student
        update_streak(student)
        check_and_unlock_badges(student)
        recalculate_score(student)

@receiver(post_save, sender=Submission)
def handle_assignment_graded(sender, instance, created, **kwargs):
    # Graded if grade field has been populated
    if instance.grade:
        student = instance.student
        update_streak(student)
        check_and_unlock_badges(student)
        recalculate_score(student)
