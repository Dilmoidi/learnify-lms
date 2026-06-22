from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy

from .models import Quiz, Question, Result
from .forms import QuizForm, QuestionForm
from apps.courses.models import Course, Enrollment
from apps.accounts.views import ApprovedInstructorRequiredMixin

# Student - Attempt Quiz
@login_required
def take_quiz(request, course_slug, quiz_id):
    course = get_object_or_404(Course, slug=course_slug)
    quiz = get_object_or_404(Quiz, pk=quiz_id, course=course)
    user = request.user
    
    # Check enrollment
    if user.role == 'student' and hasattr(user, 'student_profile'):
        enrollment = Enrollment.objects.filter(student=user.student_profile, course=course).first()
        if not enrollment:
            messages.error(request, "You must be enrolled in this course to attempt quizzes.")
            return redirect('courses:course_detail', slug=course_slug)
    elif not user.is_superuser:
        messages.error(request, "Only students enrolled in this course can attempt quizzes.")
        return redirect('courses:course_detail', slug=course_slug)

    questions = quiz.questions.all()
    if not questions.exists():
        messages.warning(request, "This quiz does not have any questions yet.")
        return redirect('courses:course_detail', slug=course_slug)

    if request.method == 'POST':
        score = 0
        total_questions = questions.count()
        
        for q in questions:
            user_ans = request.POST.get(f'question_{q.id}')
            if user_ans and int(user_ans) == q.correct_option:
                score += 1
                
        percentage = int((score / total_questions) * 100) if total_questions > 0 else 0
        passed = percentage >= quiz.pass_percentage
        
        # Save Result (only for student role, superusers don't save records)
        if user.role == 'student':
            student = user.student_profile
            result = Result.objects.create(
                quiz=quiz,
                student=student,
                score=score,
                total_questions=total_questions,
                passed=passed
            )
            
            # Check if all lessons are complete and all quizzes are passed to award certificate
            # We will handle certificate check inside the certificate app or here. Let's do it in a helper.
            from apps.certificates.views import check_and_award_certificate
            check_and_award_certificate(enrollment)
            
        return render(request, 'quizzes/quiz_result.html', {
            'quiz': quiz,
            'course': course,
            'score': score,
            'total_questions': total_questions,
            'percentage': percentage,
            'passed': passed,
            'pass_percentage': quiz.pass_percentage
        })

    return render(request, 'quizzes/take_quiz.html', {
        'quiz': quiz,
        'course': course,
        'questions': questions
    })


# Instructor Views - Quiz CRUD
class QuizCreateView(ApprovedInstructorRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/quiz_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs.get('course_id'), instructor=request.user.instructor_profile)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        messages.success(self.request, f"Quiz '{form.instance.title}' created successfully! Now add questions.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def get_success_url(self):
        return reverse('quizzes:quiz_questions_manage', kwargs={'quiz_id': self.object.id})


class QuizUpdateView(ApprovedInstructorRequiredMixin, UpdateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'quizzes/quiz_form.html'

    def get_queryset(self):
        return Quiz.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.get_object().course
        return context

    def form_valid(self, form):
        messages.success(self.request, "Quiz settings updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})


class QuizDeleteView(ApprovedInstructorRequiredMixin, DeleteView):
    model = Quiz
    template_name = 'quizzes/quiz_confirm_delete.html'

    def get_queryset(self):
        return Quiz.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Quiz deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Instructor Manage Quiz Questions
@login_required
def quiz_questions_manage(request, quiz_id):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if user.role == 'instructor' and quiz.course.instructor != user.instructor_profile:
        messages.error(request, "You are not authorized to manage this quiz.")
        return redirect('dashboard')

    questions = quiz.questions.all()
    
    return render(request, 'quizzes/quiz_questions_manage.html', {
        'quiz': quiz,
        'questions': questions
    })


# Question CRUD
class QuestionCreateView(ApprovedInstructorRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'quizzes/question_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.quiz = get_object_or_404(Quiz, pk=self.kwargs.get('quiz_id'), course__instructor=request.user.instructor_profile)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.quiz = self.quiz
        messages.success(self.request, "Question added successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.quiz
        return context

    def get_success_url(self):
        return reverse('quizzes:quiz_questions_manage', kwargs={'quiz_id': self.quiz.id})


class QuestionUpdateView(ApprovedInstructorRequiredMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'quizzes/question_form.html'

    def get_queryset(self):
        return Question.objects.filter(quiz__course__instructor=self.request.user.instructor_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quiz'] = self.get_object().quiz
        return context

    def form_valid(self, form):
        messages.success(self.request, "Question updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('quizzes:quiz_questions_manage', kwargs={'quiz_id': self.object.quiz.id})


class QuestionDeleteView(ApprovedInstructorRequiredMixin, DeleteView):
    model = Question
    template_name = 'quizzes/question_confirm_delete.html'

    def get_queryset(self):
        return Question.objects.filter(quiz__course__instructor=self.request.user.instructor_profile)

    def get_success_url(self):
        return reverse('quizzes:quiz_questions_manage', kwargs={'quiz_id': self.object.quiz.id})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Question deleted successfully.")
        return super().delete(request, *args, **kwargs)
