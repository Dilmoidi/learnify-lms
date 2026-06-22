from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
import csv
import datetime
from django.utils import timezone

from apps.accounts.models import User, Student, Instructor
from apps.courses.models import Course, Enrollment, Lesson, CourseReview, CourseCategory
from apps.assignments.models import Assignment, Submission
from apps.quizzes.models import Quiz, Result
from apps.certificates.models import Certificate

@login_required
def dashboard_home(request):
    user = request.user
    context = {}

    if user.role == 'student' and hasattr(user, 'student_profile'):
        student = user.student_profile
        enrollments = Enrollment.objects.filter(student=student).select_related('course__instructor__user', 'course__category')
        
        # Color-Coded Stats Calculations
        # 1. Teal: Enrolled and Completed
        total_enrolled = enrollments.count()
        completed_courses = enrollments.filter(is_completed=True).count()
        
        # 2. Amber: Pending Assignments & Upcoming Quizzes
        # Assignments where the student hasn't submitted yet
        all_student_assignments = Assignment.objects.filter(course__enrollments__student=student)
        submitted_assignments_ids = Submission.objects.filter(student=student).values_list('assignment_id', flat=True)
        pending_assignments_qs = all_student_assignments.exclude(id__in=submitted_assignments_ids).select_related('course')
        pending_assignments = pending_assignments_qs.count()
        
        # Quizzes in enrolled courses that student hasn't taken yet (filter out quizzes with 0 questions)
        all_student_quizzes = Quiz.objects.filter(course__enrollments__student=student).annotate(q_count=Count('questions')).filter(q_count__gt=0)
        taken_quizzes_ids = Result.objects.filter(student=student).values_list('quiz_id', flat=True)
        pending_quizzes_qs = all_student_quizzes.exclude(id__in=taken_quizzes_ids).select_related('course')
        pending_quizzes = pending_quizzes_qs.count()
        
        # 3. Pink: Certificates & Recent Activity
        certificates = Certificate.objects.filter(student=student).select_related('course')
        recent_results = Result.objects.filter(student=student).select_related('quiz__course').order_by('-completed_at')[:5]
        recent_submissions = Submission.objects.filter(student=student).select_related('assignment__course').order_by('-submitted_at')[:5]

        # Assemble context
        context.update({
            'role': 'student',
            'enrollments': enrollments,
            'total_enrolled': total_enrolled,
            'completed_courses': completed_courses,
            'pending_assignments': pending_assignments,
            'pending_quizzes': pending_quizzes,
            'pending_assignments_list': pending_assignments_qs,
            'pending_quizzes_list': pending_quizzes_qs,
            'certificates': certificates,
            'recent_results': recent_results,
            'recent_submissions': recent_submissions
        })
        
    elif user.role == 'instructor' and hasattr(user, 'instructor_profile'):
        instructor = user.instructor_profile
        
        # Instructor profile approval warning
        if not instructor.is_approved:
            return render(request, 'dashboard/instructor_pending.html')
            
        courses = Course.objects.filter(instructor=instructor).select_related('category')
        
        # Purple Accent: total courses
        total_courses = courses.count()
        
        # Teal Accent: total students
        total_students = Enrollment.objects.filter(course__instructor=instructor).count()
        
        # Amber Accent: pending grading
        pending_grading = Submission.objects.filter(
            assignment__course__instructor=instructor, 
            status='submitted'
        ).count()
        
        # Pink Accent: course reviews and ratings
        recent_reviews = CourseReview.objects.filter(course__instructor=instructor).select_related('student__user', 'course')[:5]
        
        # Recent submissions to grade
        recent_submissions = Submission.objects.filter(
            assignment__course__instructor=instructor
        ).select_related('assignment', 'student__user').order_by('-submitted_at')[:5]

        context.update({
            'role': 'instructor',
            'courses': courses,
            'total_courses': total_courses,
            'total_students': total_students,
            'pending_grading': pending_grading,
            'recent_reviews': recent_reviews,
            'recent_submissions': recent_submissions
        })
        
    elif user.role == 'admin' or user.is_superuser:
        # Admin stats
        total_users = User.objects.count()
        total_students = Student.objects.count()
        total_instructors = Instructor.objects.count()
        total_courses = Course.objects.count()
        
        pending_instructors = Instructor.objects.filter(is_approved=False).select_related('user')
        all_instructors = Instructor.objects.select_related('user').prefetch_related('courses').order_by('-is_approved', '-user__date_joined')
        recent_enrollments = Enrollment.objects.select_related('student__user', 'course').order_by('-enrolled_at')[:5]
        recent_courses = Course.objects.select_related('instructor__user').order_by('-created_at')[:5]

        # 1. Analytics - Course Popularity
        top_courses = Course.objects.annotate(enrollment_count=Count('enrollments')).order_by('-enrollment_count')[:5]
        course_popularity_labels = [c.title for c in top_courses]
        course_popularity_counts = [c.enrollment_count for c in top_courses]

        # 2. Analytics - Category Distribution
        categories_qs = CourseCategory.objects.annotate(course_count=Count('courses'))
        category_labels = [cat.name for cat in categories_qs]
        category_counts = [cat.course_count for cat in categories_qs]

        # 3. Analytics - Enrollments over the last 7 days
        today = timezone.now().date()
        last_7_days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        enrollment_counts = []
        day_labels = []
        for day in last_7_days:
            day_labels.append(day.strftime('%b %d'))
            count = Enrollment.objects.filter(enrolled_at__date=day).count()
            enrollment_counts.append(count)

        # 4. System Activities
        activities = []
        # Registrations
        for u in User.objects.order_by('-date_joined')[:5]:
            activities.append({
                'icon': 'bi-person-plus text-purple-accent',
                'text': f"New user @{u.username} ({u.get_role_display()}) registered.",
                'time': u.date_joined
            })
        # Enrollments
        for e in Enrollment.objects.select_related('student__user', 'course').order_by('-enrolled_at')[:5]:
            activities.append({
                'icon': 'bi-mortarboard text-teal',
                'text': f"Student @{e.student.user.username} enrolled in '{e.course.title}'.",
                'time': e.enrolled_at
            })
        # Course creations
        for c in Course.objects.select_related('instructor__user').order_by('-created_at')[:5]:
            activities.append({
                'icon': 'bi-book text-purple-accent',
                'text': f"Instructor @{c.instructor.user.username} created course '{c.title}'.",
                'time': c.created_at
            })
        # Reviews
        for r in CourseReview.objects.select_related('student__user', 'course').order_by('-created_at')[:5]:
            activities.append({
                'icon': 'bi-star-fill text-amber',
                'text': f"Student @{r.student.user.username} reviewed '{r.course.title}' with {r.rating} stars.",
                'time': r.created_at
            })
        # Sort all activities by time descending
        activities.sort(key=lambda x: x['time'], reverse=True)
        recent_activities = activities[:8]

        context.update({
            'role': 'admin',
            'total_users': total_users,
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_courses': total_courses,
            'pending_instructors': pending_instructors,
            'all_instructors': all_instructors,
            'recent_enrollments': recent_enrollments,
            'recent_courses': recent_courses,
            'course_popularity_labels': course_popularity_labels,
            'course_popularity_counts': course_popularity_counts,
            'category_labels': category_labels,
            'category_counts': category_counts,
            'day_labels': day_labels,
            'enrollment_counts': enrollment_counts,
            'recent_activities': recent_activities,
        })
        
    return render(request, 'dashboard/dashboard.html', context)


def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)


@user_passes_test(is_admin)
def admin_export_courses_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="courses_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Course Title', 'Category', 'Instructor', 'Enrolled Students', 'Lessons Count', 'Average Rating', 'Created Date'])
    
    courses = Course.objects.select_related('category', 'instructor__user').prefetch_related('enrollments', 'lessons')
    for c in courses:
        writer.writerow([
            c.title,
            c.category.name if c.category else 'N/A',
            c.instructor.user.get_full_name() or c.instructor.user.username,
            c.enrollments.count(),
            c.lessons.count(),
            c.average_rating,
            c.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    return response


@user_passes_test(is_admin)
def admin_export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Role', 'Status', 'Date Joined'])
    
    users = User.objects.all()
    for u in users:
        writer.writerow([
            u.username,
            u.email,
            u.first_name,
            u.last_name,
            u.get_role_display(),
            'Active' if u.is_active else 'Inactive',
            u.date_joined.strftime('%Y-%m-%d %H:%M')
        ])
    return response


@user_passes_test(is_admin)
def admin_export_instructors_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="instructors_report.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Username', 'Email', 'First Name', 'Last Name', 'Specialization', 'Phone', 'Bio', 'Approved Status', 'Courses Count', 'Date Joined'])
    
    instructors = Instructor.objects.select_related('user').prefetch_related('courses')
    for inst in instructors:
        writer.writerow([
            inst.user.username,
            inst.user.email,
            inst.user.first_name,
            inst.user.last_name,
            inst.specialization or 'N/A',
            inst.phone or 'N/A',
            inst.user.bio or 'N/A',
            'Approved' if inst.is_approved else 'Pending Approval',
            inst.courses.count(),
            inst.user.date_joined.strftime('%Y-%m-%d %H:%M')
        ])
    return response
