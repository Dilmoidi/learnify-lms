from django.db import models

class LearningStreak(models.Model):
    student = models.OneToOneField('accounts.Student', on_delete=models.CASCADE, related_name='streak')
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.student.user.username} - Streak: {self.current_streak} days"

class Badge(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)  # e.g., 'fast_learner', 'quiz_master', 'assignment_pro', 'consistent_learner', 'course_champion'
    description = models.TextField()
    icon = models.CharField(max_length=100, default='bi-award')

    def __str__(self):
        return self.name

class StudentBadge(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'badge')

    def __str__(self):
        return f"{self.student.user.username} earned {self.badge.name}"

class SkillProgress(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    progress_percent = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('student', 'skill_name')

    def __str__(self):
        return f"{self.student.user.username} - {self.skill_name}: {self.progress_percent}%"

class LeaderboardRecord(models.Model):
    student = models.OneToOneField('accounts.Student', on_delete=models.CASCADE, related_name='leaderboard_record')
    score = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.student.user.username} - Score: {self.score}"
