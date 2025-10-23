from django import forms
from .models import Quotation, QuotationFile

class QuotationCreateForm(forms.ModelForm):
    """
    A form to create a new quotation and upload its first file.
    """
    file = forms.FileField(required=True, help_text="The original PDF or Excel file.")
    
    class Meta:
        model = Quotation
        fields = ['title', 'client_name']

class QuotationFileForm(forms.ModelForm):
    """
    A form to upload a new (revised) file to an existing quotation.
    This is used on the Quotation Detail page.
    """
    class Meta:
        model = QuotationFile
        fields = ['file', 'caption']
        widgets = {
            'caption': forms.TextInput(attrs={'placeholder': 'e.g., Revision 1 (Client Feedback)'})
        }

class QuotationStatusUpdateForm(forms.ModelForm):
    """
    A form to update the internal status notes and the status itself.
    This is also used on the Quotation Detail page.
    """
    class Meta:
        model = Quotation
        fields = ['status', 'status_notes']
        widgets = {
            'status_notes': forms.Textarea(attrs={'rows': 4}),
            'status': forms.Select(attrs={'class': 'form-select'})
        }

