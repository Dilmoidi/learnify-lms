from django import forms
from .models import Assignment, Submission

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ('title', 'description', 'due_date', 'max_marks', 'attachment')
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('submitted_file',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['submitted_file'].widget.attrs.update({'class': 'form-control'})


class GradeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('grade', 'feedback')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grade'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter Grade (e.g. 90)'})
        self.fields['feedback'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Provide feedback for the student...', 'rows': 4})
