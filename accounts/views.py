from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import CustomUser,Account,Transaction,GroupPayment, Material
from workers.models import Worker, WorkerAttendance, OutsourcedGroup
from projects.models import Project, ProjectExpense
from .forms import CustomUserCreationForm, CustomUserChangeForm, AccountForm, MaterialForm
from django.db.models import Sum, Count, Case, When, DecimalField, Q, F
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import login, logout
from collections import defaultdict
import json
from django.db.models.functions import TruncMonth
from datetime import date, datetime
from decimal import Decimal
from django.db import transaction
from .models import Invoice, InvoicePayment, Account, Transaction
from .forms import InvoiceForm, InvoicePaymentForm
from .models import Journal, JournalEntry
from .forms import JournalEntryFormSet, ContraVoucherForm

# --- Reusable Permission Checker ---
def is_admin_or_owner(user):
    return user.is_authenticated and user.role in ['admin', 'owner']

def can_manage_projects(user):
    return user.is_authenticated and user.role in ['admin', 'owner', 'supervisor']

def can_add_attendance(user):
    """ 
    Checks if the user can add attendance records. This is the new function that was missing.
    """
    return user.is_authenticated and user.role in ['admin', 'owner', 'supervisor', 'foreman']

def logout_view(request):
    """
    Handles user logout and explicitly redirects to the URL named 'login'.
    """
    logout(request)
    return redirect('login')

def role_check(role_list):
    def check(user):
        return user.is_authenticated and user.role in role_list
    return check
# --- Views ---
@login_required
def dashboard_view(request):
    today = date.today()
    
    # --- New Birthday Alert Logic ---
    birthday_workers = Worker.objects.filter(
        worker_type='own', 
        is_active=True, 
        dob__month=today.month, 
        dob__day=today.day
    )
    
    # Financial Summaries (including Pending Invoices)
    pending_invoices = Invoice.objects.annotate(
        amount_received=Sum('payments__amount', default=0, output_field=DecimalField())
    ).filter(total_amount__gt=F('amount_received'))
    
    pending_invoices_total = pending_invoices.aggregate(
        total_due=Sum(F('total_amount') - F('amount_received'))
    )['total_due'] or 0
    total_credit_due = Account.objects.filter(account_type='liability').aggregate(total=Sum('balance'))['total'] or 0
    unpaid_wages = WorkerAttendance.objects.filter(is_paid=False, worker__worker_type='outsourced').aggregate(total=Sum('total_wage'))['total'] or 0
    total_payable = total_credit_due + unpaid_wages

    # Project and Worker Counts
    projects_qs = Project.objects.filter_for_user(request.user)
    active_projects_count = projects_qs.filter(status='active').count()
    completed_projects_count = projects_qs.filter(status='completed').count()
    worker_counts = Worker.objects.filter(is_active=True).aggregate(
        total_workers=Count('id'),
        own_workers=Count('id', filter=Q(worker_type='own')),
        outsourced_workers=Count('id', filter=Q(worker_type='outsourced'))
    )

    # Recent Transactions & Chart Data
    recent_transactions = Transaction.objects.select_related('account').order_by('-date')[:5]
    six_months_ago = today - timedelta(days=180)
    monthly_income = Transaction.objects.filter(date__gte=six_months_ago, transaction_type='credit').annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    monthly_expenses = Transaction.objects.filter(date__gte=six_months_ago, transaction_type='debit').annotate(month=TruncMonth('date')).values('month').annotate(total=Sum('amount')).order_by('month')
    
    chart_data = defaultdict(lambda: {'income': 0, 'expenses': 0})
    for item in monthly_income: chart_data[item['month'].strftime('%b %Y')]['income'] = float(item['total'])
    for item in monthly_expenses: chart_data[item['month'].strftime('%b %Y')]['expenses'] = float(item['total'])
    sorted_chart_data = sorted(chart_data.items(), key=lambda x: datetime.strptime(x[0], '%b %Y'))

    context = {
        'birthday_workers': birthday_workers, # Added the birthday list to the context
        'pending_invoices_total': pending_invoices_total,
        'total_credit_due': total_payable,
        'active_projects_count': active_projects_count,
        'completed_projects_count': completed_projects_count,
        'total_workers': worker_counts['total_workers'],
        'own_workers': worker_counts['own_workers'],
        'outsourced_workers': worker_counts['outsourced_workers'],
        'recent_transactions': recent_transactions,
        'chart_labels': json.dumps([item[0] for item in sorted_chart_data]),
        'chart_income_values': json.dumps([item[1]['income'] for item in sorted_chart_data]),
        'chart_expense_values': json.dumps([item[1]['expenses'] for item in sorted_chart_data]),
    }
    return render(request, 'dashboard.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def payable_list_view(request):
    """
    Groups unpaid wages by OutsourcedGroup and calculates the total for each.
    This version is corrected to use 'is_paid=False'.
    """
    unpaid_attendances = WorkerAttendance.objects.filter(
        is_paid=False,  # Corrected from payment__isnull=True
        worker__worker_type='outsourced'
    ).select_related('worker__group')

    grouped_totals = defaultdict(Decimal)
    for att in unpaid_attendances:
        if att.worker.group:
            grouped_totals[att.worker.group] += att.total_wage

    sorted_grouped_totals = dict(sorted(grouped_totals.items(), key=lambda item: item[0].name))

    context = {
        'grouped_totals': sorted_grouped_totals,
        'total_unpaid': sum(grouped_totals.values()),
    }
    return render(request, 'accounts/payable_list.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def mark_attendance_paid_view(request, pk):
    """
    Marks a single attendance record as paid and redirects back to the payables list.
    """
    attendance = get_object_or_404(WorkerAttendance, pk=pk)
    if request.method == 'POST':
        attendance.is_paid = True
        attendance.save()
        messages.success(request, f"Wage for {attendance.worker.name} on {attendance.date} marked as paid.")
    return redirect('payable_list')

@login_required
@user_passes_test(role_check(['admin', 'owner']))
def user_list_view(request):
    # Corrected the context variable name from 'users' to 'user_list'
    users = CustomUser.objects.all().order_by('username')
    return render(request, 'accounts/user_list.html', {'user_list': users})

@login_required
@user_passes_test(is_admin_or_owner)
def user_create_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'Create New User'})

@login_required
@user_passes_test(is_admin_or_owner)
def user_update_view(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user_list')
    else:
        form = CustomUserChangeForm(instance=user)
    return render(request, 'accounts/user_form.html', {'form': form, 'title': f'Edit User: {user.username}'})

@login_required
@user_passes_test(is_admin_or_owner)
def user_delete_view(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect('user_list')
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    # For GET request, you would typically show a confirmation page
    # But for simplicity here we redirect. A modal is better (implemented in templates).
    return redirect('user_list')

# @login_required
# @user_passes_test(is_admin_or_owner)
# def account_list_view(request):
#     """
#     Displays a list of financial accounts, optionally filtered by type.
#     """
#     account_type = request.GET.get('type')
#     accounts = Account.objects.all()
#     title = "All Accounts"
    
#     if account_type:
#         accounts = accounts.filter(account_type=account_type)
#         title = f"{account_type.replace('_', ' ').title()} Accounts"

#     total_balance = accounts.aggregate(total=Sum('balance'))['total'] or 0
    
#     context = {
#         'accounts': accounts,
#         'title': title,
#         'total_balance': total_balance,
#     }
#     return render(request, 'accounts/account_list.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def group_payment_detail_view(request, group_id):
    """
    Displays payment details for a group and handles the form submission
    for making partial or full payments with correct transaction logic.
    """
    group = get_object_or_404(OutsourcedGroup.objects.select_related('leader'), pk=group_id)
    
    if request.method == 'POST':
        amount_paid_str = request.POST.get('amount')
        payment_date_str = request.POST.get('payment_date')
        
        if amount_paid_str and payment_date_str:
            amount_paid = Decimal(amount_paid_str)
            payment_date = date.fromisoformat(payment_date_str)

            bank_account = Account.objects.filter(Q(account_type='asset') | Q(account_type='income')).order_by('account_type').first()
            if not bank_account:
                messages.error(request, "Payment failed: No 'Asset' or 'Income' type account found to pay from. Please create one.")
                return redirect('group_payment_detail', group_id=group.id)

            with transaction.atomic():
                # Determine the correct transaction type to DECREASE the account's balance.
                transaction_type = 'credit' if bank_account.account_type == 'asset' else 'debit'

                # 1. ALWAYS create the financial transaction for the amount paid.
                Transaction.objects.create(
                    account=bank_account,
                    transaction_type=transaction_type,
                    amount=amount_paid,
                    date=payment_date,
                    description=f"Payment to outsourced group: {group.name}",
                    created_by=request.user
                )
                
                # 2. Identify which full attendance records this payment can cover.
                unpaid_for_group = WorkerAttendance.objects.filter(worker__group=group, is_paid=False).order_by('date')
                
                pks_to_pay = []
                amount_covered = Decimal(0)
                for att in unpaid_for_group:
                    if (amount_covered + att.total_wage) <= amount_paid:
                        pks_to_pay.append(att.pk)
                        amount_covered += att.total_wage
                    else:
                        break
                
                if pks_to_pay:
                    # 3. Perform a bulk update on the records that were fully covered.
                    WorkerAttendance.objects.filter(pk__in=pks_to_pay).update(is_paid=True)
                    messages.success(request, f"Payment of Đ{amount_paid} recorded. Đ{amount_covered} of this was applied to clear the oldest unpaid wages.")
                else:
                    messages.info(request, f"Payment of Đ{amount_paid} recorded. This amount was not enough to clear any specific daily wages, but your bank balance has been updated.")

            return redirect('group_payment_detail', group_id=group.id)

    # This part handles displaying the page data (GET request)
    all_attendances = WorkerAttendance.objects.filter(
        worker__group=group
    ).select_related('worker', 'project').order_by('date')

    unpaid_attendances = all_attendances.filter(is_paid=False)
    paid_attendances = all_attendances.filter(is_paid=True)

    total_owed = unpaid_attendances.aggregate(total=Sum('total_wage'))['total'] or 0
    total_paid = paid_attendances.aggregate(total=Sum('total_wage'))['total'] or 0

    unpaid_by_date = defaultdict(list)
    for att in unpaid_attendances:
        unpaid_by_date[att.date].append(att)

    context = {
        'group': group,
        'unpaid_by_date': dict(sorted(unpaid_by_date.items())),
        'total_owed': total_owed,
        'total_paid': total_paid,
    }
    return render(request, 'accounts/group_payment_detail.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def group_pay_all_view(request, group_id):
    """
    Marks all unpaid attendance records for a group as paid.
    """
    group = get_object_or_404(OutsourcedGroup, pk=group_id)
    if request.method == 'POST':
        with transaction.atomic():
            unpaid_for_group = WorkerAttendance.objects.filter(worker__group=group, is_paid=False)
            
            # Create a single debit transaction for the total amount being paid
            total_payment = unpaid_for_group.aggregate(total=Sum('total_wage'))['total'] or 0
            bank_account = Account.objects.filter(account_type='asset').first()

            if bank_account and total_payment > 0:
                Transaction.objects.create(
                    account=bank_account,
                    transaction_type='debit',
                    amount=total_payment,
                    date=date.today(),
                    description=f"Bulk payment for outsourced group: {group.name}",
                    created_by=request.user
                )
                # Now, update the records
                unpaid_for_group.update(is_paid=True)
                messages.success(request, f"All unpaid wages for group '{group.name}' have been marked as paid and debited from {bank_account.name}.")
            elif not bank_account:
                 messages.error(request, "Payment failed: No 'Asset' account found.")
            else:
                 messages.info(request, "No unpaid wages to process.")

    return redirect('group_payment_detail', group_id=group_id)

@login_required
@user_passes_test(is_admin_or_owner)
def account_list_view(request):
    """
    Displays a list of financial accounts, optionally filtered by type.
    """
    account_type = request.GET.get('all')
    accounts = Account.objects.all()
    title = "Bank Accounts"
    
    if account_type:
        accounts = accounts.filter(account_type=account_type)
        title = f"{dict(Account.ACCOUNT_TYPES).get(account_type, 'Unknown')} Accounts"

    total_balance = accounts.aggregate(total=Sum('balance'))['total'] or 0
    
    context = {
        'accounts': accounts,
        'title': title,
        'total_balance': total_balance,
    }
    return render(request, 'accounts/account_list.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def account_create_view(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully.')
            return redirect('account_list')
    else:
        form = AccountForm()
    return render(request, 'accounts/account_form.html', {'form': form, 'title': 'Create New Account'})

@login_required
@user_passes_test(is_admin_or_owner)
def account_update_view(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account updated successfully.')
            return redirect('account_list')
    else:
        form = AccountForm(instance=account)
    return render(request, 'accounts/account_form.html', {'form': form, 'title': f'Edit Account: {account.name}'})

@login_required
@user_passes_test(is_admin_or_owner)
def material_list_view(request):
    """
    Displays a list of all materials in the inventory.
    """
    materials = Material.objects.all()
    return render(request, 'accounts/material_list.html', {'materials': materials})

@login_required
@user_passes_test(is_admin_or_owner)
def material_create_view(request):
    """
    Handles the creation of a new material using material_form.html.
    """
    if request.method == 'POST':
        form = MaterialForm(request.POST)
        if form.is_valid():
            material = form.save(commit=False)
            # Ensure quantity on hand matches initial quantity on creation
            material.quantity_on_hand = material.initial_quantity
            material.save()
            messages.success(request, f'Material "{material.name}" added to inventory.')
            return redirect('material_list')
    else:
        form = MaterialForm()
    return render(request, 'accounts/material_form.html', {'form': form, 'title': 'Add New Material'})

@login_required
@user_passes_test(is_admin_or_owner)
def material_update_view(request, pk):
    """
    Handles the editing of an existing material using material_form.html.
    """
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            messages.success(request, f'Material "{material.name}" updated successfully.')
            return redirect('material_list')
    else:
        form = MaterialForm(instance=material)
    return render(request, 'accounts/material_form.html', {'form': form, 'title': f'Edit Material: {material.name}'})

@login_required
@user_passes_test(is_admin_or_owner)
def material_delete_view(request, pk):
    """
    Handles the deletion of a material.
    """
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        material_name = material.name
        material.delete()
        messages.success(request, f'Material "{material_name}" has been deleted.')
    return redirect('material_list')

@login_required
@user_passes_test(is_admin_or_owner)
def invoice_list_view(request):
    """ Displays a list of all invoices. """
    invoices = Invoice.objects.select_related('project').all()
    return render(request, 'accounts/invoice_list.html', {'invoices': invoices})

@login_required
@user_passes_test(is_admin_or_owner)
def invoice_create_view(request):
    """
    Handles the creation of a new invoice. This view renders the form in your Canvas.
    """
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Invoice created successfully.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm()
    return render(request, 'accounts/invoice_form.html', {'form': form, 'title': 'Create New Invoice'})

@login_required
@user_passes_test(is_admin_or_owner)
def invoice_detail_view(request, pk):
    """
    Displays details for a single invoice and handles recording new payments.
    """
    invoice = get_object_or_404(Invoice.objects.select_related('project'), pk=pk)
    
    if request.method == 'POST':
        payment_form = InvoicePaymentForm(request.POST)
        if payment_form.is_valid():
            # Find a bank account to deposit the payment into
            bank_account = Account.objects.filter(account_type='asset').first()
            if not bank_account:
                messages.error(request, "Payment failed: No 'Asset' account found to receive the payment. Please create one.")
                return redirect('invoice_detail', pk=invoice.pk)

            with transaction.atomic():
                # 1. Save the payment record for the invoice
                payment = payment_form.save(commit=False)
                payment.invoice = invoice
                payment.created_by = request.user
                payment.save()

                # 2. Create a financial transaction to increase the bank balance
                # A payment RECEIVED into an Asset account is a DEBIT.
                Transaction.objects.create(
                    account=bank_account,
                    transaction_type='debit',
                    amount=payment.amount,
                    date=payment.payment_date,
                    description=f"Payment received for invoice: {invoice.title}",
                    created_by=request.user
                )
            
            messages.success(request, 'Payment recorded and bank balance updated.')
            return redirect('invoice_detail', pk=invoice.pk)
        else:
            # If the form is invalid, an error message will now be shown
            messages.error(request, 'Please correct the errors below.')
    else:
        payment_form = InvoicePaymentForm()

    context = {
        'invoice': invoice,
        'payment_form': payment_form,
    }
    return render(request, 'accounts/invoice_detail.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def invoice_update_view(request, pk):
    """
    Handles the editing of an existing invoice. This is the view you requested.
    """
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice)
        if form.is_valid():
            form.save()
            messages.success(request, 'Invoice updated successfully.')
            return redirect('invoice_list')
    else:
        form = InvoiceForm(instance=invoice)
    return render(request, 'accounts/invoice_form.html', {'form': form, 'title': f'Edit Invoice: {invoice.title}'})

@login_required
@user_passes_test(is_admin_or_owner)
def journal_list_view(request):
    """ (Read) Displays a list of all journal transactions. """
    journals = Journal.objects.select_related('created_by', 'project').prefetch_related('entries__account').all()
    return render(request, 'accounts/journal_list.html', {'journals': journals})

@login_required
@user_passes_test(is_admin_or_owner)
def journal_create_view(request):
    """ (Create) A dynamic view to create various types of journal vouchers. """
    voucher_type = request.GET.get('type', 'journal')
    
    if voucher_type == 'contra':
        form = ContraVoucherForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            data = form.cleaned_data
            with transaction.atomic():
                journal = Journal.objects.create(
                    date=data['date'],
                    description=data['description'],
                    voucher_type='contra',
                    created_by=request.user
                )
                JournalEntry.objects.create(journal=journal, account=data['from_account'], credit=data['amount'])
                JournalEntry.objects.create(journal=journal, account=data['to_account'], debit=data['amount'])
            messages.success(request, 'Contra entry recorded successfully.')
            return redirect('journal_list')
        
        context = {'form': form, 'voucher_type': voucher_type, 'title': 'Create Contra Voucher'}
        return render(request, 'accounts/journal_form.html', context)

    else: # Handle standard Journal, Payment, or Receipt vouchers
        journal = Journal(voucher_type=voucher_type, created_by=request.user)
        if request.method == 'POST':
            formset = JournalEntryFormSet(request.POST, instance=journal)
            if formset.is_valid():
                with transaction.atomic():
                    journal.date = request.POST.get('date')
                    journal.description = request.POST.get('description')
                    journal.save()
                    formset.save()
                messages.success(request, f'{voucher_type.title()} voucher recorded successfully.')
                return redirect('journal_list')
        else:
            formset = JournalEntryFormSet(instance=journal)
            
        context = {'formset': formset, 'voucher_type': voucher_type, 'title': f'Create {voucher_type.title()} Voucher'}
        return render(request, 'accounts/journal_form.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def journal_update_view(request, pk):
    """ (Update) Handles the editing of an existing journal entry. """
    journal = get_object_or_404(Journal, pk=pk)
    
    # Contra entries are simple and should be deleted/recreated, not edited.
    if journal.voucher_type == 'contra':
        messages.error(request, "Contra entries cannot be edited. Please delete and recreate it if necessary.")
        return redirect('journal_list')

    if request.method == 'POST':
        formset = JournalEntryFormSet(request.POST, instance=journal)
        if formset.is_valid():
            with transaction.atomic():
                journal.date = request.POST.get('date')
                journal.description = request.POST.get('description')
                journal.save()
                formset.save()
            messages.success(request, 'Journal entry updated successfully.')
            return redirect('journal_list')
    else:
        formset = JournalEntryFormSet(instance=journal)

    context = {
        'formset': formset,
        'journal': journal,
        'voucher_type': journal.voucher_type,
        'title': f'Edit {journal.voucher_type.title()} Voucher'
    }
    return render(request, 'accounts/journal_form.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def journal_delete_view(request, pk):
    """ (Delete) Handles the deletion of a journal entry. """
    journal = get_object_or_404(Journal, pk=pk)
    if request.method == 'POST':
        journal_desc = str(journal)
        journal.delete()
        messages.success(request, f'Journal entry "{journal_desc}" has been deleted.')
    return redirect('journal_list')
