from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.gamification.models import LeaderboardRecord
from apps.courses.models import Course, Enrollment

@login_required
def leaderboard_view(request):
    # 1. Top 10 Overall
    overall_records = LeaderboardRecord.objects.all().select_related('student__user').order_by('-score')[:10]
    
    # User's own rank
    user_record = None
    user_rank = None
    if hasattr(request.user, 'student_profile'):
        student = request.user.student_profile
        user_record = LeaderboardRecord.objects.filter(student=student).first()
        if user_record:
            # Count records with higher score to get rank
            user_rank = LeaderboardRecord.objects.filter(score__gt=user_record.score).count() + 1

    # 2. Course-wise Leaderboard
    selected_course_id = request.GET.get('course_id')
    course_rankings = []
    courses = Course.objects.filter(is_published=True)

    if selected_course_id:
        # Get top 10 enrollments in this course ordered by progress
        course_rankings = Enrollment.objects.filter(course_id=selected_course_id).select_related('student__user').order_by('-progress_percentage', '-enrolled_at')[:10]

    return render(request, 'leaderboard/leaderboard.html', {
        'overall_records': overall_records,
        'user_record': user_record,
        'user_rank': user_rank,
        'courses': courses,
        'selected_course_id': selected_course_id,
        'course_rankings': course_rankings,
    })
