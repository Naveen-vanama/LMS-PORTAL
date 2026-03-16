from django import forms
from .models import FileResource


class FileResourceForm(forms.ModelForm):
    class Meta:
        model = FileResource
        fields = ('title', 'description', 'resource_type', 'batch', 'file', 'external_url', 'is_visible')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'batch': forms.Select(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields['batch'].queryset = course.batches.all()
            self.fields['batch'].required = False
