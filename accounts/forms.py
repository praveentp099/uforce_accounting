from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from .models import Account, Material, Invoice, InvoicePayment
from django import forms

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'role', 'is_active')

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'balance']

class MaterialForm(forms.ModelForm):
    """
    A form for creating and editing materials in the inventory.
    """
    class Meta:
        model = Material
        fields = [
            'name', 'supplier', 'unit', 
            'initial_quantity', 'quantity_on_hand', 
            'price_per_unit', 'low_stock_threshold'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On creation, quantity_on_hand should default to initial_quantity
        if not self.instance.pk:
            self.fields['quantity_on_hand'].initial = self.fields['initial_quantity'].initial

class InvoiceForm(forms.ModelForm):
    """
    Form for creating a new invoice.
    """
    class Meta:
        model = Invoice
        fields = ['project', 'title', 'issue_date', 'due_date', 'total_amount']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

class InvoicePaymentForm(forms.ModelForm):
    """
    Form for recording a payment against an invoice.
    """
    class Meta:
        model = InvoicePayment
        fields = ['amount', 'payment_date']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }