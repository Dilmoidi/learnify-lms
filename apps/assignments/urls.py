from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    # Student actions
    path('submit/<int:assignment_id>/', views.submit_assignment, name='submit_assignment'),
    
    # Instructor actions
    path('instructor/assignments/', views.instructor_assignments_list, name='instructor_assignments'),
    path('instructor/course/<int:course_id>/assignment/add/', views.AssignmentCreateView.as_view(), name='assignment_create'),
    path('instructor/assignment/<int:pk>/edit/', views.AssignmentUpdateView.as_view(), name='assignment_edit'),
    path('instructor/assignment/<int:pk>/delete/', views.AssignmentDeleteView.as_view(), name='assignment_delete'),
    path('instructor/assignment/<int:assignment_id>/submissions/', views.assignment_submissions_list, name='assignment_submissions'),
    path('instructor/submission/<int:submission_id>/grade/', views.grade_submission, name='grade_submission'),
]
