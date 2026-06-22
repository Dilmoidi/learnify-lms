from django import forms
from .models import Course, Lesson, DiscussionThread, DiscussionReply, CourseReview, Announcement

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ('title', 'description', 'category', 'thumbnail', 'is_published')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})
        self.fields['is_published'].widget.attrs.update({'class': 'form-check-input'})


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('title', 'description', 'video_file', 'video_url', 'pdf_notes', 'order')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})


class DiscussionThreadForm(forms.ModelForm):
    class Meta:
        model = DiscussionThread
        fields = ('title', 'content')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Thread Title'})
        self.fields['content'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Write your question or comment here...', 'rows': 4})


class DiscussionReplyForm(forms.ModelForm):
    class Meta:
        model = DiscussionReply
        fields = ('content',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Write a reply...', 'rows': 3})


class CourseReviewForm(forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ('rating', 'comment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].widget.attrs.update({'class': 'form-select'})
        self.fields['comment'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Write your review...', 'rows': 3})


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'content')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Announcement Title'})
        self.fields['content'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Write the announcement details here...', 'rows': 4})
