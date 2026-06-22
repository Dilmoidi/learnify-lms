from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Student views
    path('', views.CourseListView.as_view(), name='course_list'),
    path('<slug:slug>/', views.CourseDetailView.as_view(), name='course_detail'),
    path('<slug:slug>/enroll/', views.enroll_in_course, name='enroll_in_course'),
    path('<slug:course_slug>/lessons/<int:lesson_id>/', views.lesson_view, name='lesson_view'),
    path('<slug:course_slug>/lessons/<int:lesson_id>/complete/', views.mark_lesson_completed, name='mark_lesson_completed'),
    
    # Forum & reviews
    path('<slug:course_slug>/forums/create/', views.create_discussion_thread, name='create_discussion_thread'),
    path('<slug:course_slug>/forums/<int:thread_id>/', views.discussion_thread_detail, name='discussion_thread_detail'),
    path('<slug:course_slug>/reviews/create/', views.create_course_review, name='create_course_review'),
    
    # Instructor Course actions
    path('instructor/my-courses/', views.InstructorCourseListView.as_view(), name='instructor_courses'),
    path('instructor/course/create/', views.CourseCreateView.as_view(), name='course_create'),
    path('instructor/course/<int:pk>/edit/', views.CourseUpdateView.as_view(), name='course_edit'),
    path('instructor/course/<int:pk>/delete/', views.CourseDeleteView.as_view(), name='course_delete'),
    
    # Instructor Lesson actions
    path('instructor/course/<int:course_id>/lesson/add/', views.LessonCreateView.as_view(), name='lesson_add'),
    path('instructor/lesson/<int:pk>/edit/', views.LessonUpdateView.as_view(), name='lesson_edit'),
    path('instructor/lesson/<int:pk>/delete/', views.LessonDeleteView.as_view(), name='lesson_delete'),

    # Instructor Announcements
    path('<slug:course_slug>/announcements/create/', views.create_announcement, name='create_announcement'),
    path('<slug:course_slug>/announcements/<int:pk>/delete/', views.delete_announcement, name='delete_announcement'),

    # Instructor Enrolled Students & Track Student Progress
    path('instructor/students/progress/', views.instructor_students_progress, name='instructor_students_progress'),
    path('instructor/students/progress/<int:enrollment_id>/', views.instructor_student_detail_progress, name='instructor_student_detail_progress'),
]
