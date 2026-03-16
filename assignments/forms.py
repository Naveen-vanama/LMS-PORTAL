from django import forms
from .models import AssignmentSubmission, Assignment


class AssignmentSubmissionForm(forms.ModelForm):
    """Form for student submitting an assignment."""

    class Meta:
        model = AssignmentSubmission
        fields = ['answer_text', 'code_submission']
        widgets = {
            'answer_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 8,
                'placeholder': 'Write your detailed answer here...',
            }),
            'code_submission': forms.Textarea(attrs={
                'class': 'form-control code-editor',
                'rows': 12,
                'placeholder': '# Paste or write your code here...',
                'spellcheck': 'false',
            }),
        }

    def __init__(self, *args, assignment=None, **kwargs):
        super().__init__(*args, **kwargs)
        if assignment:
            if assignment.assignment_type == 'coding':
                self.fields['answer_text'].required = False
                self.fields['answer_text'].widget = forms.HiddenInput()
                self.fields['code_submission'].required = True
                self.fields['code_submission'].label = 'Your Code Solution'
            else:
                self.fields['code_submission'].required = False
                self.fields['code_submission'].widget = forms.HiddenInput()
                self.fields['answer_text'].required = True
                self.fields['answer_text'].label = 'Your Answer'


class InstructorReviewForm(forms.ModelForm):
    """Form for instructors to override AI grading."""

    class Meta:
        model = AssignmentSubmission
        fields = ['manual_score', 'manual_feedback']
        widgets = {
            'manual_score': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
            }),
            'manual_feedback': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Provide your feedback to the student...',
            }),
        }
        labels = {
            'manual_score': 'Override Score',
            'manual_feedback': 'Manual Feedback',
        }


class AssignmentCreateForm(forms.ModelForm):
    """Form for instructors to create assignments."""

    class Meta:
        model = Assignment
        fields = ['course', 'lesson', 'title', 'description', 'assignment_type', 'max_score']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'assignment_type': forms.Select(attrs={'class': 'form-select'}),
            'max_score': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'course': forms.Select(attrs={'class': 'form-select'}),
            'lesson': forms.Select(attrs={'class': 'form-select'}),
        }
