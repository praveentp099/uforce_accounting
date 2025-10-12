from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import AbstractUser

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
        return f"Payment of ${self.amount} to {self.group.name} on {self.payment_date}"

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

