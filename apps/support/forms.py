from django import forms
from .models import SupportTicket, TicketReply, SupportAgent

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['category', 'subject', 'description', 'priority', 'attachment']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select bg-sidebar border-default text-primary'}),
            'subject': forms.TextInput(attrs={'class': 'form-control bg-sidebar border-default text-primary', 'placeholder': 'Brief summary of the issue'}),
            'description': forms.Textarea(attrs={'class': 'form-control bg-sidebar border-default text-primary', 'rows': 5, 'placeholder': 'Detailed description of the issue...'}),
            'priority': forms.Select(attrs={'class': 'form-select bg-sidebar border-default text-primary'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control bg-sidebar border-default text-primary'}),
        }

class TicketReplyForm(forms.ModelForm):
    class Meta:
        model = TicketReply
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'class': 'form-control bg-sidebar border-default text-primary', 'rows': 3, 'placeholder': 'Write your reply...'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control bg-sidebar border-default text-primary'}),
        }

class TicketStatusAssignForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['status', 'assigned_to']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select bg-sidebar border-default text-primary'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select bg-sidebar border-default text-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate support agent dropdown with users having support profiles
        self.fields['assigned_to'].queryset = SupportAgent.objects.select_related('user').all()
        self.fields['assigned_to'].required = False
