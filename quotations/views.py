from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Quotation
from .forms import QuotationForm
from accounts.views import is_admin_or_owner

@login_required
def quotation_list_view(request):
    quotations = Quotation.objects.select_related('uploaded_by').all()
    context = {
        'pending_quotations': quotations.filter(status='pending'),
        'approved_quotations': quotations.filter(status='approved'),
        'revised_quotations': quotations.filter(status='revised'),
    }
    return render(request, 'quotations/quotation_list.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_create_view(request):
    if request.method == 'POST':
        form = QuotationForm(request.POST, request.FILES)
        if form.is_valid():
            quotation = form.save(commit=False)
            quotation.uploaded_by = request.user
            quotation.save()
            messages.success(request, 'Quotation uploaded successfully.')
            return redirect('quotation_list')
    else:
        form = QuotationForm()
    return render(request, 'quotations/quotation_form.html', {'form': form})

@login_required
@user_passes_test(is_admin_or_owner)
def quotation_update_status_view(request, pk, status):
    quotation = get_object_or_404(Quotation, pk=pk)
    if request.method == 'POST':
        quotation.status = status
        quotation.save()
        messages.success(request, f'Quotation "{quotation.title}" moved to {status.title()}.')
    return redirect('quotation_list')

