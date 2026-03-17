from django import forms
from .models import Course, Batch, Group, Announcement, Lesson
from users.models import CustomUser
from django.db.models import Q


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ('title', 'code', 'description', 'instructor', 'status', 'credits', 'thumbnail')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'instructor': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'credits': forms.NumberInput(attrs={'class': 'form-control'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instructor'].queryset = CustomUser.objects.filter(role__in=['instructor', 'admin'])


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ('name', 'start_date', 'end_date', 'max_students')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ('name', 'members')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'members': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch
        if batch:
            enrolled_students = CustomUser.objects.filter(
                enrollments__batch=batch
            )
            self.fields['members'].queryset = enrolled_students

    def clean_members(self):
        members = self.cleaned_data.get('members')
        batch = getattr(self, 'instance', None).batch if getattr(self, 'instance', None) and hasattr(self.instance, 'batch') else None
        # If batch is not on instance, it might be passed in __init__
        if not batch and hasattr(self, 'batch'):
            batch = self.batch

        if batch and members:
            for student in members:
                # Check if this student is already in another group for ANY batch of this course
                other_groups = Group.objects.filter(batch__course=batch.course, members=student)
                if self.instance.pk:
                    other_groups = other_groups.exclude(pk=self.instance.pk)
                
                if other_groups.exists():
                    raise forms.ValidationError(f"Student {student.username} is already assigned to group '{other_groups.first().name}' in this course. Only one group per course is allowed.")
        return members


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ('title', 'content', 'batch')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Announcement Title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Important message...'}),
            'batch': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields['batch'].queryset = course.batches.all()
            self.fields['batch'].empty_label = "All Batches"


class AIGeneratorForm(forms.Form):
    topic = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Python Functions'})
    )
    pdf_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('topic') and not cleaned_data.get('pdf_file'):
            raise forms.ValidationError("Please provide either a topic or a PDF file.")
        return cleaned_data


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('title', 'content')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
        }
