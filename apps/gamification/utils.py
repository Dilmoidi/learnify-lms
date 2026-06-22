import datetime
from django.db import models
from django.utils import timezone
from apps.notifications.models import Notification
from .models import LearningStreak, Badge, StudentBadge, SkillProgress, LeaderboardRecord

def create_notification(user, message):
    Notification.objects.create(user=user, message=message)

def ensure_badges_exist():
    badges_data = [
        {
            'code': 'fast_learner',
            'name': 'Fast Learner',
            'description': 'Awarded for completing at least 3 lessons on the platform.',
            'icon': 'bi-rocket-takeoff'
        },
        {
            'code': 'quiz_master',
            'name': 'Quiz Master',
            'description': 'Awarded for scoring 100% on any course quiz.',
            'icon': 'bi-patch-check-fill'
        },
        {
            'code': 'assignment_pro',
            'name': 'Assignment Pro',
            'description': 'Awarded for receiving a score of 90% or higher on any graded assignment.',
            'icon': 'bi-file-earmark-check-fill'
        },
        {
            'code': 'consistent_learner',
            'name': 'Consistent Learner',
            'description': 'Awarded for maintaining a daily learning streak of 7 days or more.',
            'icon': 'bi-calendar-heart'
        },
        {
            'code': 'course_champion',
            'name': 'Course Champion',
            'description': 'Awarded for fully completing a course syllabus to 100% progress.',
            'icon': 'bi-trophy-fill'
        }
    ]
    for b in badges_data:
        Badge.objects.get_or_create(code=b['code'], defaults={
            'name': b['name'],
            'description': b['description'],
            'icon': b['icon']
        })

def update_streak(student):
    streak, created = LearningStreak.objects.get_or_create(student=student)
    today = timezone.localdate()
    yesterday = today - datetime.timedelta(days=1)

    if streak.last_activity_date == today:
        # Already logged activity today, do not increment streak
        return
    elif streak.last_activity_date == yesterday:
        # Increment streak
        streak.current_streak += 1
        if streak.current_streak > streak.longest_streak:
            streak.longest_streak = streak.current_streak
    else:
        # Streak broken, reset to 1
        streak.current_streak = 1
        if streak.longest_streak == 0:
            streak.longest_streak = 1

    streak.last_activity_date = today
    streak.save()

    # Recalculate leaderboard points
    recalculate_score(student)
    # Check consistent learner badge
    check_and_unlock_badges(student)

def update_skill_progress(student, course):
    if not course.category:
        return
    
    category = course.category
    # Compute lessons completed in this category out of total lessons in this category
    from apps.courses.models import Lesson, LessonProgress
    total_lessons = Lesson.objects.filter(course__category=category).count()
    if total_lessons == 0:
        progress = 100
    else:
        completed_lessons = LessonProgress.objects.filter(
            enrollment__student=student,
            lesson__course__category=category,
            is_completed=True
        ).count()
        progress = int((completed_lessons / total_lessons) * 100)
    
    skill, _ = SkillProgress.objects.get_or_create(student=student, skill_name=category.name)
    skill.progress_percent = progress
    skill.save()

def recalculate_score(student):
    from apps.quizzes.models import Result
    from apps.assignments.models import Submission
    from apps.courses.models import Enrollment, DiscussionReply

    # 1. Quiz Score: total score percentage sum
    quiz_results = Result.objects.filter(student=student)
    quiz_score = sum(r.score for r in quiz_results) * 10 # 10 pts per correct question / percent ratio

    # 2. Assignment Grades: sum of graded submissions
    submissions = Submission.objects.filter(student=student, grade__isnull=False)
    # Convert grade to integer
    def get_val(g):
        try: return int(float(g))
        except: return 0
    assignment_score = sum(get_val(sub.grade) for sub in submissions) * 5

    # 3. Course completions
    completions = Enrollment.objects.filter(student=student, is_completed=True).count()
    completion_score = completions * 100

    # 4. Streak Score
    streak, _ = LearningStreak.objects.get_or_create(student=student)
    streak_score = streak.current_streak * 15

    # 5. Badge Unlocks (50 pts per badge)
    badge_score = StudentBadge.objects.filter(student=student).count() * 50

    # 6. Forum Best Answers (15 pts per best reply)
    best_answers_score = DiscussionReply.objects.filter(user=student.user, is_best_answer=True).count() * 15

    total_score = quiz_score + assignment_score + completion_score + streak_score + badge_score + best_answers_score

    record, _ = LeaderboardRecord.objects.get_or_create(student=student)
    record.score = total_score
    record.save()

def check_and_unlock_badges(student):
    ensure_badges_exist()

    # 1. Fast Learner: completed >= 3 lessons
    from apps.courses.models import LessonProgress
    completed_count = LessonProgress.objects.filter(enrollment__student=student, is_completed=True).count()
    if completed_count >= 3:
        unlock_badge(student, 'fast_learner')

    # 2. Quiz Master: 100% on any quiz
    from apps.quizzes.models import Result
    # Check results via loop for accuracy
    for r in Result.objects.filter(student=student):
        total = r.quiz.questions.count()
        if total > 0 and r.score == total:
            unlock_badge(student, 'quiz_master')
            break

    # 3. Assignment Pro: score >= 90%
    from apps.assignments.models import Submission
    for sub in Submission.objects.filter(student=student, grade__isnull=False):
        try:
            val = float(sub.grade)
            # Max score on assignment is typically 100 or standard. Let's check if grade is >= 90
            if val >= 90.0:
                unlock_badge(student, 'assignment_pro')
                break
        except ValueError:
            pass

    # 4. Consistent Learner: streak >= 7 days
    streak, _ = LearningStreak.objects.get_or_create(student=student)
    if streak.current_streak >= 7:
        unlock_badge(student, 'consistent_learner')

    # 5. Course Champion: completed >= 1 course
    from apps.courses.models import Enrollment
    has_completion = Enrollment.objects.filter(student=student, is_completed=True).exists()
    if has_completion:
        unlock_badge(student, 'course_champion')

def unlock_badge(student, badge_code):
    try:
        badge = Badge.objects.get(code=badge_code)
        sb, created = StudentBadge.objects.get_or_create(student=student, badge=badge)
        if created:
            # Send notification
            create_notification(
                user=student.user,
                message=f"🏆 Achievement unlocked! You have earned the '{badge.name}' badge: {badge.description}"
            )
            # Add extra points for unlocking a badge!
            record, _ = LeaderboardRecord.objects.get_or_create(student=student)
            record.score += 50
            record.save()
    except Badge.DoesNotExist:
        pass
