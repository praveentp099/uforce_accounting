from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
import json

from .models import Quotation, QuotationFile
from .forms import QuotationCreateForm, QuotationFileForm, QuotationStatusUpdateForm
from accounts.views import is_admin_or_owner

@login_required
def quotation_list_view(request):
    """
    Displays lists of quotations, separated by their new statuses,
    and calculates data for the approval rate pie chart.
    """
    quotations = Quotation.objects.select_related('uploaded_by').all()
    
    # Calculate counts for the pie chart (Approval Rate vs. Rejected)
    stats = quotations.aggregate(
        approved=Count('id', filter=Q(status='approved')),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    
    # Calculate count for pending/reviewing
    pending_count = quotations.filter(
        status__in=['pending', 'under_review', 'revised']
    ).count()

    context = {
        'pending_quotations': quotations.filter(status='pending'),
        'review_quotations': quotations.filter(status='under_review'),
        'revised_quotations': quotations.filter(status='revised'),
        'approved_quotations': quotations.filter(status='approved'),
        'rejected_quotations': quotations.filter(status='rejected'),
        
        'chart_labels': json.dumps(['Approved', 'Rejected']),
        'chart_data': json.dumps([stats['approved'], stats['rejected']]),
        'pending_count': pending_count,
        'stats': stats, # Added the stats dictionary to the context
    }
    return render(request, 'quotations/quotation_list.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_create_view(request):
    """
    Handles the creation of a new Quotation and its first QuotationFile.
    """
    if request.method == 'POST':
        form = QuotationCreateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                # First, create the parent quotation object
                quotation = form.save(commit=False)
                quotation.uploaded_by = request.user
                quotation.save()
                
                # Then, create the first file associated with it
                QuotationFile.objects.create(
                    quotation=quotation,
                    file=form.cleaned_data['file'],
                    caption='Original',
                    uploaded_by=request.user
                )
            messages.success(request, 'Quotation uploaded successfully.')
            return redirect('quotation_list')
    else:
        form = QuotationCreateForm()
    return render(request, 'quotations/quotation_form.html', {'form': form, 'title': 'Upload Quotation'})

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_detail_view(request, pk):
    """
    Displays details for a single quotation and handles:
    1. Uploading new file revisions.
    2. Updating the status and status notes.
    """
    quotation = get_object_or_404(Quotation.objects.prefetch_related('files__uploaded_by'), pk=pk)
    
    status_form = QuotationStatusUpdateForm(instance=quotation)
    file_form = QuotationFileForm()

    if request.method == 'POST':
        if 'upload_revision' in request.POST:
            # Handle the "Upload a Revision" form
            file_form = QuotationFileForm(request.POST, request.FILES)
            if file_form.is_valid():
                with transaction.atomic():
                    new_file = file_form.save(commit=False)
                    new_file.quotation = quotation
                    new_file.uploaded_by = request.user
                    new_file.save()
                    
                    # Set status to 'Revised'
                    quotation.status = 'revised'
                    quotation.save()
                    
                messages.success(request, 'New file revision uploaded.')
                return redirect('quotation_detail', pk=pk)
        
        elif 'update_status' in request.POST:
            # Handle the "Update Status & Notes" form
            status_form = QuotationStatusUpdateForm(request.POST, instance=quotation)
            if status_form.is_valid():
                updated_quotation = status_form.save()
                # If status is NOT 'approved', clear the approved_file link
                if updated_quotation.status != 'approved':
                    updated_quotation.approved_file = None
                    updated_quotation.save()
                messages.success(request, 'Quotation status updated.')
                return redirect('quotation_detail', pk=pk)
            
    context = {
        'quotation': quotation,
        'status_form': status_form,
        'file_form': file_form,
    }
    return render(request, 'quotations/quotation_detail.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_approve_file_view(request, quotation_pk, file_pk):
    """
    Sets a specific file as the 'approved_file' for a quotation
    and marks the quotation as 'Approved'.
    """
    if request.method == 'POST':
        quotation = get_object_or_404(Quotation, pk=quotation_pk)
        file_to_approve = get_object_or_404(QuotationFile, pk=file_pk, quotation=quotation)
        
        quotation.approved_file = file_to_approve
        quotation.status = 'approved'
        quotation.save()
        
        messages.success(request, f'File "{file_to_approve.caption}" has been set as the approved version.')
    return redirect('quotation_detail', pk=quotation_pk)

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_reject_view(request, pk):
    """
    A view to quickly reject a quotation.
    """
    if request.method == 'POST':
        quotation = get_object_or_404(Quotation, pk=pk)
        quotation.status = 'rejected'
        quotation.approved_file = None
        quotation.save()
        messages.warning(request, f'Quotation "{quotation.title}" has been rejected.')
    
    return redirect('quotation_list')



@login_required
@user_passes_test(is_admin_or_owner)
def quotation_update_status_view(request, pk, status):
    """
    This view is called by the "Move to Approved/Rejected/Pending" buttons.
    """
    quotation = get_object_or_404(Quotation, pk=pk)
    if request.method == 'POST' and status in ['pending', 'approved', 'rejected']:
        quotation.status = status
        quotation.save()
        messages.success(request, f'Quotation "{quotation.title}" moved to {status.title()}.')
    
    # If the request came from the detail page, return there.
    # Otherwise, default to the list page.
    referer = request.META.get('HTTP_REFERER')
    if referer and str(quotation.get_absolute_url()) in referer:
        return redirect('quotation_detail', pk=pk)
    return redirect('quotation_list')



