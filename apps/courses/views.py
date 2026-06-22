from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db.models import Q

from .models import CourseCategory, Course, Lesson, Enrollment, LessonProgress, DiscussionThread, DiscussionReply, CourseReview, Announcement
from .forms import CourseForm, LessonForm, DiscussionThreadForm, DiscussionReplyForm, CourseReviewForm, AnnouncementForm
from apps.accounts.models import Student, Instructor

from apps.accounts.views import ApprovedInstructorRequiredMixin


# Browse and List Courses
class CourseListView(ListView):
    model = Course
    template_name = 'courses/course_list'
    context_object_name = 'courses'
    paginate_by = 6

    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True).select_related('category', 'instructor__user')
        search_query = self.request.GET.get('search')
        category_slug = self.request.GET.get('category')

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = CourseCategory.objects.all()
        context['selected_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('search')
        return context


# Course Detail Page
class CourseDetailView(DetailView):
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        user = self.request.user
        
        is_enrolled = False
        enrollment = None
        user_review = None

        if user.is_authenticated:
            if user.role == 'student' and hasattr(user, 'student_profile'):
                enrollment = Enrollment.objects.filter(student=user.student_profile, course=course).first()
                if enrollment:
                    is_enrolled = True
                    user_review = CourseReview.objects.filter(course=course, student=user.student_profile).first()
            elif user.role == 'instructor' and course.instructor == getattr(user, 'instructor_profile', None):
                is_enrolled = True  # Instructors can see their own course syllabus and contents
            elif user.is_superuser:
                is_enrolled = True

        context['is_enrolled'] = is_enrolled
        context['enrollment'] = enrollment
        context['lessons'] = course.lessons.all()
        context['threads'] = course.discussion_threads.all().select_related('user')
        context['reviews'] = course.reviews.all().select_related('student__user')
        
        # Add Quizzes and Assignments
        context['assignments'] = course.assignments.all()
        context['quizzes'] = course.quizzes.all()
        
        # Load student submissions & quiz results
        submissions_dict = {}
        results_dict = {}
        if user.is_authenticated and is_enrolled and user.role == 'student':
            from apps.assignments.models import Submission
            from apps.quizzes.models import Result
            student_profile = user.student_profile
            
            # Map assignment_id -> submission object
            submissions_dict = {sub.assignment_id: sub for sub in Submission.objects.filter(student=student_profile, assignment__course=course)}
            
            # Map quiz_id -> best result object
            for res in Result.objects.filter(student=student_profile, quiz__course=course):
                if res.quiz_id not in results_dict or res.score > results_dict[res.quiz_id].score:
                    results_dict[res.quiz_id] = res

        context['submissions_dict'] = submissions_dict
        context['results_dict'] = results_dict
        
        # Discussion thread form
        context['thread_form'] = DiscussionThreadForm()
        # Review Form
        if is_enrolled and user.role == 'student' and not user_review:
            context['review_form'] = CourseReviewForm()
        else:
            context['review_form'] = None
            
        context['user_review'] = user_review
        context['announcements'] = course.announcements.all().order_by('-created_at')
        context['announcement_form'] = AnnouncementForm()
        return context


# Student Enrolls in Course
@login_required
def enroll_in_course(request, slug):
    if request.user.role != 'student':
        messages.error(request, "Only students can enroll in courses.")
        return redirect('courses:course_detail', slug=slug)
        
    course = get_object_or_404(Course, slug=slug, is_published=True)
    student = request.user.student_profile
    
    enrollment, created = Enrollment.objects.get_or_create(student=student, course=course)
    
    if created:
        # Create LessonProgress instances for all lessons in this course
        for lesson in course.lessons.all():
            LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        messages.success(request, f"Successfully enrolled in {course.title}!")
    else:
        messages.info(request, f"You are already enrolled in {course.title}.")
        
    return redirect('courses:course_detail', slug=slug)


# Lesson View
@login_required
def lesson_view(request, course_slug, lesson_id):
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    user = request.user
    
    is_authorized = False
    enrollment = None
    
    # Check if student is enrolled, or if user is the course instructor
    if user.role == 'student' and hasattr(user, 'student_profile'):
        enrollment = Enrollment.objects.filter(student=user.student_profile, course=course).first()
        if enrollment:
            is_authorized = True
    elif user.role == 'instructor' and course.instructor == getattr(user, 'instructor_profile', None):
        is_authorized = True
    elif user.is_superuser:
        is_authorized = True
        
    if not is_authorized:
        messages.error(request, "Access denied. You must be enrolled in this course to view lessons.")
        return redirect('courses:course_detail', slug=course_slug)

    # Get lesson progress state
    lesson_progress = None
    if enrollment:
        lesson_progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)

    # Get syllabus with progress indicators
    syllabus_progress = []
    for les in course.lessons.all():
        completed = False
        if enrollment:
            lp = LessonProgress.objects.filter(enrollment=enrollment, lesson=les).first()
            if lp:
                completed = lp.is_completed
        syllabus_progress.append({
            'lesson': les,
            'completed': completed
        })

    # Next / Prev lesson logic
    lessons_list = list(course.lessons.all())
    current_index = lessons_list.index(lesson)
    prev_lesson = lessons_list[current_index - 1] if current_index > 0 else None
    next_lesson = lessons_list[current_index + 1] if current_index < len(lessons_list) - 1 else None

    return render(request, 'courses/lesson_view.html', {
        'course': course,
        'lesson': lesson,
        'enrollment': enrollment,
        'lesson_progress': lesson_progress,
        'syllabus_progress': syllabus_progress,
        'prev_lesson': prev_lesson,
        'next_lesson': next_lesson
    })


# Mark Lesson Completed
@login_required
def mark_lesson_completed(request, course_slug, lesson_id):
    if request.user.role != 'student':
        messages.error(request, "Only students can track lesson progress.")
        return redirect('courses:lesson_view', course_slug=course_slug, lesson_id=lesson_id)
        
    course = get_object_or_404(Course, slug=course_slug)
    lesson = get_object_or_404(Lesson, pk=lesson_id, course=course)
    student = request.user.student_profile
    
    enrollment = get_object_or_404(Enrollment, student=student, course=course)
    progress_record = get_object_or_404(LessonProgress, enrollment=enrollment, lesson=lesson)
    
    # Toggle complete
    if not progress_record.is_completed:
        progress_record.is_completed = True
        progress_record.completed_at = timezone.now()
        messages.success(request, f"Lesson '{lesson.title}' marked as completed!")
    else:
        progress_record.is_completed = False
        progress_record.completed_at = None
        messages.info(request, f"Lesson '{lesson.title}' marked as incomplete.")
        
    progress_record.save()
    enrollment.update_progress()
    
    # Direct to next lesson if complete and exists, else redirect back to current lesson
    next_l = course.lessons.filter(order__gt=lesson.order).first()
    if progress_record.is_completed and next_l:
        # Pre-create progress for next lesson if missing
        LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=next_l)
        return redirect('courses:lesson_view', course_slug=course.slug, lesson_id=next_l.pk)
        
    return redirect('courses:lesson_view', course_slug=course.slug, lesson_id=lesson.pk)


# Create Discussion Thread
@login_required
def create_discussion_thread(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if request.method == 'POST':
        form = DiscussionThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.course = course
            thread.user = request.user
            thread.save()
            messages.success(request, "Discussion thread posted successfully!")
    return redirect('courses:course_detail', slug=course_slug)


# Discussion Thread Details & Replies
@login_required
def discussion_thread_detail(request, course_slug, thread_id):
    course = get_object_or_404(Course, slug=course_slug)
    thread = get_object_or_404(DiscussionThread, pk=thread_id, course=course)
    replies = thread.replies.all().select_related('user')
    
    if request.method == 'POST':
        form = DiscussionReplyForm(request.POST)
        if form.is_valid():
            reply = form.save(commit=False)
            reply.thread = thread
            reply.user = request.user
            reply.save()
            messages.success(request, "Reply posted!")
            return redirect('courses:discussion_thread_detail', course_slug=course_slug, thread_id=thread_id)
    else:
        form = DiscussionReplyForm()
        
    return render(request, 'courses/discussion_thread_detail.html', {
        'course': course,
        'thread': thread,
        'replies': replies,
        'form': form
    })


# Create Course Review
@login_required
def create_course_review(request, course_slug):
    if request.user.role != 'student':
        messages.error(request, "Only students can submit reviews.")
        return redirect('courses:course_detail', slug=course_slug)
        
    course = get_object_or_404(Course, slug=course_slug)
    student = request.user.student_profile
    
    # Check if enrolled
    enrollment = Enrollment.objects.filter(student=student, course=course).first()
    if not enrollment:
        messages.error(request, "You must be enrolled in this course to review it.")
        return redirect('courses:course_detail', slug=course_slug)

    # Check duplicate
    if CourseReview.objects.filter(course=course, student=student).exists():
        messages.error(request, "You have already reviewed this course.")
        return redirect('courses:course_detail', slug=course_slug)

    if request.method == 'POST':
        form = CourseReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.course = course
            review.student = student
            review.save()
            messages.success(request, "Thank you for your feedback! Review submitted.")
            
    return redirect('courses:course_detail', slug=course_slug)


# Instructor Course Dashboard Views (CRUD)
class InstructorCourseListView(ApprovedInstructorRequiredMixin, ListView):
    model = Course
    template_name = 'courses/instructor_course_list.html'
    context_object_name = 'courses'

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user.instructor_profile).select_related('category')


class CourseCreateView(ApprovedInstructorRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def form_valid(self, form):
        form.instance.instructor = self.request.user.instructor_profile
        messages.success(self.request, f"Course '{form.instance.title}' created successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:instructor_courses')


class CourseUpdateView(ApprovedInstructorRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user.instructor_profile)

    def form_valid(self, form):
        messages.success(self.request, "Course updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:instructor_courses')


class CourseDeleteView(ApprovedInstructorRequiredMixin, DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    success_url = reverse_lazy('courses:instructor_courses')

    def get_queryset(self):
        return Course.objects.filter(instructor=self.request.user.instructor_profile)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Course deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Lessons CRUD
class LessonCreateView(ApprovedInstructorRequiredMixin, CreateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.course = get_object_or_404(Course, pk=self.kwargs.get('course_id'), instructor=request.user.instructor_profile)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.course = self.course
        messages.success(self.request, f"Lesson '{form.instance.title}' added successfully!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.course.slug})


class LessonUpdateView(ApprovedInstructorRequiredMixin, UpdateView):
    model = Lesson
    form_class = LessonForm
    template_name = 'courses/lesson_form.html'

    def get_queryset(self):
        return Lesson.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.get_object().course
        return context

    def form_valid(self, form):
        messages.success(self.request, "Lesson updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})


class LessonDeleteView(ApprovedInstructorRequiredMixin, DeleteView):
    model = Lesson
    template_name = 'courses/lesson_confirm_delete.html'

    def get_queryset(self):
        return Lesson.objects.filter(course__instructor=self.request.user.instructor_profile)

    def get_success_url(self):
        return reverse('courses:course_detail', kwargs={'slug': self.object.course.slug})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Lesson deleted successfully.")
        return super().delete(request, *args, **kwargs)


@login_required
def create_announcement(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)
    if not ((request.user.role == 'instructor' and course.instructor == getattr(request.user, 'instructor_profile', None)) or request.user.is_superuser):
        messages.error(request, "You are not authorized to post announcements for this course.")
        return redirect('courses:course_detail', slug=course_slug)
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.course = course
            ann.save()
            messages.success(request, "Announcement posted successfully!")
        else:
            messages.error(request, "Failed to post announcement. Please check the inputs.")
            
    return redirect('courses:course_detail', slug=course_slug)


@login_required
def delete_announcement(request, course_slug, pk):
    course = get_object_or_404(Course, slug=course_slug)
    if not ((request.user.role == 'instructor' and course.instructor == getattr(request.user, 'instructor_profile', None)) or request.user.is_superuser):
        messages.error(request, "You are not authorized to delete announcements.")
        return redirect('courses:course_detail', slug=course_slug)
        
    announcement = get_object_or_404(Announcement, pk=pk, course=course)
    announcement.delete()
    messages.success(request, "Announcement deleted successfully.")
    return redirect('courses:course_detail', slug=course_slug)


@login_required
def instructor_students_progress(request):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    instructor = user.instructor_profile
    courses = Course.objects.filter(instructor=instructor)
    
    selected_course_id = request.GET.get('course_id')
    enrollments = Enrollment.objects.filter(course__instructor=instructor).select_related('student__user', 'course').order_by('-enrolled_at')
    
    if selected_course_id:
        enrollments = enrollments.filter(course_id=selected_course_id)
        
    return render(request, 'courses/instructor_students_progress.html', {
        'courses': courses,
        'enrollments': enrollments,
        'selected_course_id': selected_course_id,
    })


@login_required
def instructor_student_detail_progress(request, enrollment_id):
    user = request.user
    if not ((user.role == 'instructor' and user.instructor_profile.is_approved) or user.is_superuser):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    # Security check: ensure course belongs to the instructor
    if not (user.is_superuser or enrollment.course.instructor == user.instructor_profile):
        messages.error(request, "You are not authorized to view this student's progress.")
        return redirect('dashboard')
        
    student = enrollment.student
    course = enrollment.course
    
    # Get all lessons and their completion state for this enrollment
    lesson_progresses = enrollment.lesson_progresses.all().select_related('lesson').order_by('lesson__order')
    
    # Quiz results for this student in this course
    from apps.quizzes.models import Result
    quiz_results = Result.objects.filter(student=student, quiz__course=course).select_related('quiz').order_by('-completed_at')
    
    # Assignment submissions for this student in this course
    from apps.assignments.models import Submission
    submissions = Submission.objects.filter(student=student, assignment__course=course).select_related('assignment').order_by('-submitted_at')
    
    return render(request, 'courses/instructor_student_detail_progress.html', {
        'enrollment': enrollment,
        'student': student,
        'course': course,
        'lesson_progresses': lesson_progresses,
        'quiz_results': quiz_results,
        'submissions': submissions,
    })


def home_landing(request):
    categories = CourseCategory.objects.all()
    total_students = Student.objects.count()
    total_instructors = Instructor.objects.count()
    total_courses = Course.objects.count()
    
    category_data = []
    for cat in categories:
        lesson_count = Lesson.objects.filter(course__category=cat).count()
        category_data.append({
            'category': cat,
            'lesson_count': lesson_count
        })
        
    context = {
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_courses': total_courses,
        'category_data': category_data,
    }
    return render(request, 'home_landing.html', context)
