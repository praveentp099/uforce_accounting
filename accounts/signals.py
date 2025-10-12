from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Transaction

@receiver([post_save, post_delete], sender=Transaction)
def update_account_balance_on_transaction_change(sender, instance, **kwargs):
    """
    When a Transaction is saved or deleted, trigger the balance update
    on its related Account.
    """
    if instance.account:
        instance.account.update_balance()
