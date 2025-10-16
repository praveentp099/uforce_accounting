from django import forms
from .models import Project, ProjectExpense, Task, ProjectPhoto, TaskPhoto, ProjectDocument

class ProjectForm(forms.ModelForm):
    """
    A form for creating and updating Projects, including all the new fields.
    """
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'client_company', 'start_date', 'end_date', 
            'budget', 'supervisor', 'priority', 'status', 
            'client_comments', 'remarks'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'client_comments': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class ProjectDocumentForm(forms.ModelForm):
    """
    A form for uploading new project documents.
    """
    class Meta:
        model = ProjectDocument
        fields = ['title', 'file']

class TaskForm(forms.ModelForm):
    """
    A form for creating new tasks, now including the start_date.
    """
    class Meta:
        model = Task
        fields = ['title', 'description', 'start_date', 'due_date']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional details about the task'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class TaskUpdateForm(forms.ModelForm):
    """ A new, separate form for EDITING existing tasks. """
    class Meta:
        model = Task
        fields = ['title', 'description', 'start_date', 'due_date', 'status', 'client_comments', 'completion_notes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'client_comments': forms.Textarea(attrs={'rows': 3}),
            'completion_notes': forms.Textarea(attrs={'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class TaskPhotoForm(forms.ModelForm):
    """
    A new form for uploading photos related to a specific task.
    """
    class Meta:
        model = TaskPhoto
        fields = ['image', 'caption']

class ProjectExpenseForm(forms.ModelForm):
    class Meta:
        model = ProjectExpense
        fields = ['project', 'expense_type', 'amount', 'description', 'date', 'receipt']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 2}),
        }

class ProjectPhotoForm(forms.ModelForm):
    """
    A form for uploading new project photos.
    """
    class Meta:
        model = ProjectPhoto
        fields = ['image', 'caption']