from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.utils import timezone

from .models import Assignment, Submission
from .forms import AssignmentForm, SubmissionForm, GradeSubmissionForm
from apps.courses.models import Course, Enrollment
from apps.accounts.views import ApprovedInstructorRequiredMixin

# Student - Submit Assignment
@login_required
def submit_assignment(request, assignment_id):
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    course = assignment.course
    user = request.user
    
    # Check enrollment
    if user.role == 'student' and hasattr(user, 'student_profile'):
        enrollment = Enrollment.objects.filter(student=user.student_profile, course=course).first()
        if not enrollment:
            messages.error(request, "You must be enrolled in this course to submit assignments.")
            return redirect('courses:course_detail', slug=course.slug)
    else:
        messages.error(request, "Only enrolled students can submit assignments.")
        return redirect('courses:course_detail', slug=course.slug)

    submission = Submission.objects.filter(assignment=assignment, student=user.student_profile).first()
    
    # Block resubmission if already graded
    if submission and submission.status == 'graded':
        messages.error(request, "This assignment has already been graded and cannot be resubmitted.")
        return redirect('courses:course_detail', slug=course.slug)

    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.assignment = assignment
            sub.student = user.student_profile
            sub.submitted_at = timezone.now()
            sub.status = 'submitted'
            sub.save()
            messages.success(request, f"Assignment '{assignment.title}' submitted successfully!")
            return redirect('courses:course_detail', slug=course.slug)
    else:
        form = SubmissionForm(instance=submission)

    return render(request, 'assignments/submit_assignment.html', {
        'assignment': assignment,
        'course': course,
        'form': form,
        'submission': submission,
        'is_late': timezone.now() > assignment.due_date
    })


# Instructor - Create Assignment
class AssignmentCreateView(ApprovedInstructorRequiredMixin, CreateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs.get('course_id'), instructor=request.user.instructor_profile)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        messages.success(self.request, f"Assignment '{form.instance.title}' created successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.course.slug})


# Instructor - Update Assignment
class AssignmentUpdateView(ApprovedInstructorRequiredMixin, UpdateView):
    model = Assignment
    form_class = AssignmentForm
    template_name = 'assignments/assignment_form.html'

    def get_queryset(self):
        return Assignment.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.get_object().course
        return context

    def form_valid(self, form):
        messages.success(self.request, "Assignment details updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})


# Instructor - Delete Assignment
class AssignmentDeleteView(ApprovedInstructorRequiredMixin, DeleteView):
    model = Assignment
    template_name = 'assignments/assignment_confirm_delete.html'

    def get_queryset(self):
        return Assignment.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Assignment deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Instructor - View Submissions list
@login_required
def assignment_submissions_list(request, assignment_id):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    assignment = get_object_or_404(Assignment, pk=assignment_id)
    if user.role == 'instructor' and assignment.course.instructor != user.instructor_profile:
        messages.error(request, "You are not authorized to view these submissions.")
        return redirect('dashboard')

    submissions = assignment.submissions.all().select_related('student__user')
    
    return render(request, 'assignments/submissions_list.html', {
        'assignment': assignment,
        'submissions': submissions
    })


# Instructor - Grade Submission
@login_required
def grade_submission(request, submission_id):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    submission = get_object_or_404(Submission, pk=submission_id)
    assignment = submission.assignment
    
    if user.role == 'instructor' and assignment.course.instructor != user.instructor_profile:
        messages.error(request, "You are not authorized to grade this submission.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = 'graded'
            
            # Simple score validation
            if sub.grade > assignment.max_marks:
                messages.error(request, f"Grade cannot exceed maximum marks of {assignment.max_marks}.")
            else:
                sub.save()
                messages.success(request, f"Grade updated for {submission.student.user.username}!")
                
                # Check for certificate awards if all coursework complete
                enrollment = Enrollment.objects.filter(student=submission.student, course=assignment.course).first()
                if enrollment:
                    from apps.certificates.views import check_and_award_certificate
                    check_and_award_certificate(enrollment)
                    
                return redirect('assignments:assignment_submissions', assignment_id=assignment.id)
    else:
        form = GradeSubmissionForm(instance=submission)

    return render(request, 'assignments/grade_submission.html', {
        'submission': submission,
        'assignment': assignment,
        'form': form
    })


@login_required
def instructor_assignments_list(request):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    instructor = user.instructor_profile
    courses = Course.objects.filter(instructor=instructor).prefetch_related('assignments__submissions')
    
    return render(request, 'assignments/instructor_assignments_list.html', {
        'courses': courses
    })
