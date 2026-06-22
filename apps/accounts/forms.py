from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Student, Instructor

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'placeholder': 'Last Name'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'placeholder': 'Email Address'}))
    
    ROLE_CHOICES = (
        ('student', 'Student (Learn, track progress, attempt quizzes)'),
        ('instructor', 'Instructor (Create courses, upload materials, grade)')
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True, widget=forms.RadioSelect)
    
    # Extra profile fields
    phone = forms.CharField(max_length=15, required=False, widget=forms.TextInput(attrs={'placeholder': 'Phone Number'}))
    specialization = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Specialization (Instructors only)'}))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        specialization = cleaned_data.get('specialization')
        
        # If instructor is chosen, specialization is recommended but optional
        if role == 'instructor' and not specialization:
            cleaned_data['specialization'] = 'General Education'
            
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data.get('role')
        user.role = role
        
        # Admin is created directly through superuser, registration only allows student or instructor
        if commit:
            user.save()
            phone = self.cleaned_data.get('phone')
            if role == 'student':
                Student.objects.create(user=user, phone=phone)
            elif role == 'instructor':
                specialization = self.cleaned_data.get('specialization')
                Instructor.objects.create(user=user, specialization=specialization, phone=phone, is_approved=False)
                
        return user


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'profile_picture', 'bio')


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ('phone',)


class InstructorProfileForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ('specialization', 'phone')
