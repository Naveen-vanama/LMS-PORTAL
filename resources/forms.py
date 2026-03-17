from django import forms
from .models import FileResource

from courses.models import Group

class FileResourceForm(forms.ModelForm):
    class Meta:
        model = FileResource
        fields = ('title', 'description', 'resource_type', 'batch', 'group', 'file', 'external_url', 'is_visible')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'group': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, course=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.course = course
            self.user = user
            self.fields['batch'].queryset = course.batches.all()
            self.fields['batch'].required = False
            
            groups_qs = Group.objects.filter(batch__course=course)
            self.is_restricted_instructor = False
            if user and not (user.is_admin_role or user == course.instructor or user.is_superuser):
                # Restrict to groups where this user is the assigned instructor
                groups_qs = groups_qs.filter(instructor=user)
                self.is_restricted_instructor = True
            
            self.fields['group'].queryset = groups_qs
            self.fields['group'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if getattr(self, 'is_restricted_instructor', False):
            group = cleaned_data.get('group')
            if not group:
                raise forms.ValidationError("You must select a group to upload resources. You are only allowed to upload to your assigned groups.")
            
            # Double check group instructor-ship
            if group.instructor != self.user:
                raise forms.ValidationError(f"You do not have permission to upload resources to group '{group.name}'.")
            
            # If limited to a group, they probably shouldn't set a batch (the group belongs to a batch anyway)
            # but we can let the model handle that if needed. 
            # Force batch to be the group's batch to avoid confusion.
            cleaned_data['batch'] = group.batch
            
        return cleaned_data
