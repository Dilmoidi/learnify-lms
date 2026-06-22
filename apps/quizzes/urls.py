from django.urls import path
from . import views

app_name = 'quizzes'

urlpatterns = [
    # Student actions
    path('course/<slug:course_slug>/take/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    
    # Instructor Quiz actions
    path('instructor/course/<int:course_id>/quiz/add/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('instructor/quiz/<int:pk>/edit/', views.QuizUpdateView.as_view(), name='quiz_edit'),
    path('instructor/quiz/<int:pk>/delete/', views.QuizDeleteView.as_view(), name='quiz_delete'),
    
    # Questions Management
    path('instructor/quiz/<int:quiz_id>/questions/', views.quiz_questions_manage, name='quiz_questions_manage'),
    path('instructor/quiz/<int:quiz_id>/question/add/', views.QuestionCreateView.as_view(), name='question_add'),
    path('instructor/question/<int:pk>/edit/', views.QuestionUpdateView.as_view(), name='question_edit'),
    path('instructor/question/<int:pk>/delete/', views.QuestionDeleteView.as_view(), name='question_delete'),
]
