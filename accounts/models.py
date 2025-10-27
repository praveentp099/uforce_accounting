from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    ROLE_CHOICES = (('admin', 'Admin'), ('owner', 'Company Owner'), ('supervisor', 'Supervisor'), ('foreman', 'Foreman'))
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username

class GroupPayment(models.Model):
    """
    This new model tracks each individual payment made to a group.
    """
    group = models.ForeignKey('workers.OutsourcedGroup', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        ordering = ['-payment_date']
    def __str__(self):
        return f"Payment of Đ{self.amount} to {self.group.name} on {self.payment_date}"

class Account(models.Model):
    ACCOUNT_TYPES = (('asset', 'Asset'), ('liability', 'Liability'), ('equity', 'Equity'), ('income', 'Income'), ('expense', 'Expense'), ('receivable', 'Accounts Receivable'))
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    def __str__(self): return self.name

    def update_balance(self):
        credit_total = self.transaction_set.filter(transaction_type='credit').aggregate(total=Sum('amount'))['total'] or 0
        debit_total = self.transaction_set.filter(transaction_type='debit').aggregate(total=Sum('amount'))['total'] or 0
        if self.account_type in ['asset', 'expense']:
            self.balance = debit_total - credit_total
        else:
            self.balance = credit_total - debit_total
        self.save()

class Transaction(models.Model):
    TRANSACTION_TYPES = (('debit', 'Debit'), ('credit', 'Credit'))
    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField()
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    def __str__(self): return f"{self.date} - {self.description}"


class Company(models.Model):
    name = models.CharField(max_length=100, default="uForce")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name

class Material(models.Model):
    """
    Represents a construction material in inventory with detailed tracking.
    """
    name = models.CharField(max_length=200, unique=True)
    supplier = models.CharField(max_length=200, blank=True)
    unit = models.CharField(max_length=50, help_text="e.g., 'piece', 'kg', 'meter'")
    
    # Quantity and Price
    initial_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Initial Quantity (Count)")
    quantity_on_hand = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Quantity Left")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Price per Unit")
    
    # Additional useful fields
    low_stock_threshold = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Get a warning when stock drops to this level.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_value(self):
        """Calculates the total monetary value of the material currently in stock."""
        return self.quantity_on_hand * self.price_per_unit

    @property
    def is_low_stock(self):
        """Returns True if the quantity on hand is at or below the threshold."""
        if self.low_stock_threshold > 0:
            return self.quantity_on_hand <= self.low_stock_threshold
        return False
    
class Invoice(models.Model):
    """
    Represents an invoice sent to a client for a project.
    """
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='invoices')
    title = models.CharField(max_length=255)
    issue_date = models.DateField()
    due_date = models.DateField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Amount to be Received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"Invoice for {self.project.name} - {self.title}"

    def get_absolute_url(self):
        return reverse('invoice_detail', kwargs={'pk': self.pk})

    @property
    def amount_received(self):
        """Calculates the total amount received from all related payments."""
        return self.payments.aggregate(total=Sum('amount'))['total'] or 0

    @property
    def balance_due(self):
        """Calculates the outstanding balance."""
        return self.total_amount - self.amount_received

    @property
    def is_paid(self):
        """Returns True if the invoice is fully paid."""
        return self.balance_due <= 0

class InvoicePayment(models.Model):
    """
    Represents a partial or full payment received for an invoice.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Payment of {self.amount} for {self.invoice.title}"
    
class Journal(models.Model):
    """
    Represents a complete accounting transaction. It is linked to a user and optionally to a project.
    """
    VOUCHER_TYPES = (
        ('journal', 'Journal Voucher'), ('payment', 'Payment Voucher'),
        ('receipt', 'Receipt Voucher'), ('contra', 'Contra Voucher'),
    )
    date = models.DateField()
    description = models.TextField()
    voucher_type = models.CharField(max_length=20, choices=VOUCHER_TYPES)
    project = models.ForeignKey('projects.Project', on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_voucher_type_display()} on {self.date}: {self.description}"

class JournalEntry(models.Model):
    """
    A single debit or credit line within a Journal. It is linked to one Account.
    """
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.account.name} {'DR' if self.debit > 0 else 'CR'} {self.debit or self.credit}"

    def clean(self):
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("An entry cannot have both a debit and a credit.")
        if self.debit == 0 and self.credit == 0:
            raise ValidationError("An entry must have either a debit or a credit.")
        
class Supplier(models.Model):
    """
    A central table to store all suppliers, vendors, rental shops, etc.
    This is the model referenced by the ProjectExpense model in your Canvas.
    """
    SUPPLIER_TYPES = (
        ('materials', 'Materials Supplier'),
        ('vehicle_rent', 'Vehicle Rental'),
        ('equipment_rent', 'Equipment Rental'),
        ('food_beverages', 'Food & Beverages'),
        ('other', 'Other'),
    )
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=SUPPLIER_TYPES, help_text="The main type of service this supplier provides.")
    contact_person = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name