from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser
from .models import Journal, JournalEntry, Account, Material, Invoice, InvoicePayment
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

class ContraVoucherForm(forms.Form):
    """
    A simplified form specifically for creating Contra entries (transfers between Asset accounts).
    """
    from_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(account_type='asset'),
        label="From Account (Credit)"
    )
    to_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(account_type='asset'),
        label="To Account (Debit)"
    )
    amount = forms.DecimalField(max_digits=12, decimal_places=2)
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        to_account = cleaned_data.get('to_account')
        if from_account and to_account and from_account == to_account:
            raise forms.ValidationError("The 'From' and 'To' accounts cannot be the same.")
        return cleaned_data

class JournalEntryForm(forms.ModelForm):
    """ A form for a single line in a journal entry. """
    class Meta:
        model = JournalEntry
        fields = ['account', 'debit', 'credit']

class BaseJournalEntryFormSet(forms.BaseInlineFormSet):
    """ Custom formset to validate that debits and credits are balanced. """
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        total_debit = sum(form.cleaned_data.get('debit', 0) for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE', False))
        total_credit = sum(form.cleaned_data.get('credit', 0) for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE', False))

        if total_debit != total_credit:
            raise forms.ValidationError('The total debit and credit amounts must be equal.')
        if total_debit == 0:
            raise forms.ValidationError('The transaction amount cannot be zero.')

# This creates the formset that will be used in the template
JournalEntryFormSet = forms.inlineformset_factory(
    Journal, JournalEntry, form=JournalEntryForm, formset=BaseJournalEntryFormSet, 
    extra=2, can_delete=True
)

