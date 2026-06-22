from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, UpdateView, TemplateView, ListView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from .models import User, Student, Instructor
from .forms import UserRegistrationForm, UserProfileForm, StudentProfileForm, InstructorProfileForm

class RegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        role = form.cleaned_data.get('role')
        if role == 'instructor':
            messages.info(self.request, "Account created successfully! Your instructor profile is pending administrator approval.")
        else:
            messages.success(self.request, "Account created successfully! You can now log in.")
        return response


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have been successfully signed out.")
        return super().dispatch(request, *args, **kwargs)


@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'accounts/profile.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        user_form = UserProfileForm(instance=user)
        
        if user.role == 'student':
            profile_form = StudentProfileForm(instance=user.student_profile)
        elif user.role == 'instructor':
            profile_form = InstructorProfileForm(instance=user.instructor_profile)
        else:
            profile_form = None
            
        return self.render_to_response({
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request, *args, **kwargs):
        user = request.user
        user_form = UserProfileForm(request.POST, request.FILES, instance=user)
        
        if user.role == 'student':
            profile_form = StudentProfileForm(request.POST, instance=user.student_profile)
        elif user.role == 'instructor':
            profile_form = InstructorProfileForm(request.POST, instance=user.instructor_profile)
        else:
            profile_form = None

        if user_form.is_valid() and (profile_form is None or profile_form.is_valid()):
            user_form.save()
            if profile_form:
                profile_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('accounts:profile')
            
        return self.render_to_response({
            'user_form': user_form,
            'profile_form': profile_form
        })


class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == 'admin' or self.request.user.is_superuser


class ApprovedInstructorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        user = self.request.user
        return (user.role == 'instructor' and 
                hasattr(user, 'instructor_profile') and 
                user.instructor_profile.is_approved) or user.is_superuser


class AdminApprovalsView(AdminRequiredMixin, ListView):
    model = Instructor
    template_name = 'accounts/admin_approvals.html'
    context_object_name = 'pending_instructors'

    def get_queryset(self):
        return Instructor.objects.filter(is_approved=False).select_related('user')


@login_required
def approve_instructor(request, pk):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        messages.error(request, "Access denied. Administrator privileges required.")
        return redirect('dashboard')
        
    instructor = get_object_or_404(Instructor, pk=pk)
    instructor.is_approved = True
    instructor.save()
    messages.success(request, f"Instructor account for {instructor.user.username} has been approved!")
    return redirect('accounts:admin_approvals')
