from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Worker, WorkerAttendance
from .forms import WorkerForm, WorkerAttendanceForm
from accounts.views import is_admin_or_owner, can_manage_projects, can_add_attendance
from projects.models import Project
from django.db.models import Sum, Count, Q
from datetime import date
from calendar import monthrange

@login_required
def worker_list_view(request):
    """
    Displays a list of active workers that can be filtered by type.
    """
    base_workers = Worker.objects.filter(is_active=True)
    type_filter = request.GET.get('type')

    counts = base_workers.aggregate(
        all=Count('id'),
        own=Count('id', filter=Q(worker_type='own')),
        outsourced=Count('id', filter=Q(worker_type='outsourced'))
    )

    if type_filter in ['own', 'outsourced']:
        display_workers = base_workers.filter(worker_type=type_filter)
    else:
        display_workers = base_workers

    context = {
        'workers': display_workers.select_related('group', 'group__leader').order_by('name'),
        'counts': counts,
        'current_filter': type_filter,
    }
    return render(request, 'workers/worker_list.html', context)

@login_required
@user_passes_test(can_manage_projects)
def worker_create_view(request):
    """
    Handles the creation of a new worker using the WorkerForm.
    """
    if request.method == 'POST':
        form = WorkerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Worker created successfully.')
            return redirect('worker_list')
    else:
        form = WorkerForm()
    return render(request, 'workers/add_worker.html', {'form': form, 'title': 'Add New Worker'})

@login_required
@user_passes_test(can_manage_projects)
def worker_update_view(request, pk):
    """
    Handles the editing of an existing worker using the WorkerForm.
    """
    worker = get_object_or_404(Worker, pk=pk)
    if request.method == 'POST':
        form = WorkerForm(request.POST, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, 'Worker updated successfully.')
            return redirect('worker_list')
    else:
        form = WorkerForm(instance=worker)
    return render(request, 'workers/add_worker.html', {'form': form, 'title': f'Edit Worker: {worker.name}'})

@login_required
@user_passes_test(is_admin_or_owner)
def worker_toggle_active_view(request, pk):
    worker = get_object_or_404(Worker, pk=pk)
    if request.method == 'POST':
        worker.is_active = not worker.is_active
        worker.save()
        status = "activated" if worker.is_active else "deactivated"
        messages.success(request, f'Worker has been {status}.')
    return redirect('worker_list')

@login_required
def attendance_list_view(request):
    """
    Displays a list of all active workers, which links to their
    individual, detailed attendance pages.
    """
    workers = Worker.objects.filter(is_active=True).order_by('name')
    return render(request, 'workers/attendance_list.html', {'workers': workers})

@login_required
def worker_detail_view(request, pk):
    """
    Displays a detailed attendance report for a single worker with
    powerful date and month filtering capabilities.
    """
    worker = get_object_or_404(Worker, pk=pk)
    today = date.today()

    # Get filter parameters from the user's request
    month_year_str = request.GET.get('month_year') # e.g., "2025-10"
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if month_year_str:
        # Filter by a specific month
        year, month = map(int, month_year_str.split('-'))
        _, last_day = monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, last_day)
        filter_description = start_date.strftime('%B %Y')
    elif start_date_str and end_date_str:
        # Filter by a custom date range
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
        filter_description = f"from {start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
    else:
        # Default to showing the current month's records
        start_date = today.replace(day=1)
        _, last_day = monthrange(today.year, today.month)
        end_date = today.replace(day=last_day)
        filter_description = "for the Current Month"

    # Query the database for the relevant attendance records
    attendances = WorkerAttendance.objects.filter(
        worker=worker,
        date__range=[start_date, end_date]
    ).select_related('project').order_by('date')

    # Calculate totals for the filtered period
    totals = attendances.aggregate(
        total_hours=Sum('hours_worked'),
        total_overtime=Sum('overtime_hours'),
        total_wages=Sum('total_wage')
    )

    context = {
        'worker': worker,
        'attendances': attendances,
        'start_date': start_date,
        'end_date': end_date,
        'filter_description': filter_description,
        'month_year_filter': f"{start_date.year}-{start_date.month:02d}",
        'totals': totals,
    }
    return render(request, 'workers/worker_detail.html', context)





@login_required
@user_passes_test(can_add_attendance)
def attendance_create_view(request, project_id=None):
    initial_data = {}
    if project_id:
        initial_data['project'] = project_id

    if request.method == 'POST':
        form = WorkerAttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.recorded_by = request.user
            attendance.save()
            messages.success(request, 'Attendance recorded successfully.')
            return redirect('project_detail', pk=attendance.project.id)
    else:
        form = WorkerAttendanceForm(initial=initial_data)

    # Limit project choices for non-admins
    if not is_admin_or_owner(request.user):
         form.fields['project'].queryset = Project.objects.filter(supervisor=request.user, status='active')

    return render(request, 'workers/attendance_form.html', {'form': form, 'title': 'Add Attendance Record'})

