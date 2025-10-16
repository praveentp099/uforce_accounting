from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Project, ProjectExpense, Task, ProjectDocument
from .forms import ProjectForm, ProjectExpenseForm, TaskForm,TaskPhotoForm, TaskUpdateForm, ProjectPhotoForm, ProjectDocumentForm
from accounts.views import is_admin_or_owner, can_manage_projects, can_add_attendance
from django.db.models import Sum, Count
from django.urls import reverse 

@login_required
def project_list_view(request):
    """
    Displays a list of projects that can be filtered by status.
    Defaults to showing all projects.
    """
    # Get the base queryset of projects visible to the current user
    base_projects = Project.objects.filter_for_user(request.user)

    # Get the status filter from the URL query parameter (e.g., ?status=active)
    status_filter = request.GET.get('status')

    # Efficiently calculate the count for each status category
    status_counts = base_projects.values('status').annotate(count=Count('id'))
    counts = {
        'all': base_projects.count(),
        'active': 0,
        'on_hold': 0,
        'completed': 0
    }
    for item in status_counts:
        counts[item['status']] = item['count']

    # Filter the projects to be displayed in the table
    if status_filter in ['active', 'on_hold', 'completed']:
        display_projects = base_projects.filter(status=status_filter)
    else:
        # If no filter is applied, show all projects
        display_projects = base_projects

    context = {
        'projects': display_projects.select_related('supervisor'),
        'counts': counts,
        'current_filter': status_filter,
    }
    return render(request, 'projects/project_list.html', context)

@login_required
@user_passes_test(can_manage_projects)
def project_detail_view(request, pk):
    """
    Displays the main dashboard for a single project, including tabs for
    tasks and documents, and handles related form submissions.
    """
    project = get_object_or_404(Project.objects.select_related('supervisor'), pk=pk)
    
    # Handle Task form submission
    if request.method == 'POST' and 'add_task' in request.POST:
        task_form = TaskForm(request.POST)
        if task_form.is_valid():
            task = task_form.save(commit=False)
            task.project = project
            task.save()
            messages.success(request, 'New task added successfully.')
            return redirect('project_detail', pk=project.pk)
    else:
        task_form = TaskForm()

    # Handle Document form submission (This uses ProjectDocumentForm)
    if request.method == 'POST' and 'upload_document' in request.POST:
        document_form = ProjectDocumentForm(request.POST, request.FILES)
        if document_form.is_valid():
            document = document_form.save(commit=False)
            document.project = project
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Document uploaded successfully.')
            # Redirect back to the same page, but with the documents tab active
            return redirect(f"{project.get_absolute_url()}?tab=documents")
    else:
        document_form = ProjectDocumentForm()

    tasks = project.tasks.all()
    documents = project.documents.select_related('uploaded_by').all()
    remaining_budget = project.budget - project.actual_cost
    
    # This is the new logic to fetch recent expenses for the template
    recent_expenses = project.expenses.select_related('recorded_by').all()[:5]


    context = {
        'project': project,
        'tasks': tasks,
        'documents': documents,
        'recent_expenses': recent_expenses, # Added recent_expenses to the context
        'task_form': task_form,
        'document_form': document_form,
        'remaining_budget': remaining_budget,
    }
    return render(request, 'projects/project_detail.html', context)

@login_required
@user_passes_test(can_manage_projects)
def task_update_view(request, pk):
    """
    Handles the editing of an existing task within a modal.
    """
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskUpdateForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            # This special template sends a message to the parent window to close the modal
            return render(request, 'projects/task_form_success.html') 
    else:
        form = TaskUpdateForm(instance=task)
    
    return render(request, 'projects/task_form.html', {'form': form, 'task': task})

@login_required
@user_passes_test(can_manage_projects)
def task_toggle_status_view(request, pk):
    """
    Handles the multi-step progression of a task's status:
    To Do -> In Progress -> Completed -> (Restart) In Progress
    """
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        if task.status == 'todo':
            task.status = 'in_progress'
            messages.info(request, f'Task "{task.title}" has been started.')
        elif task.status == 'in_progress':
            task.status = 'completed'
            messages.success(request, f'Task "{task.title}" marked as completed.')
        elif task.status == 'completed':
            task.status = 'in_progress' # Restart the task
            messages.warning(request, f'Task "{task.title}" has been restarted.')
        task.save()
    return redirect('project_detail', pk=task.project.pk)

@login_required
@user_passes_test(can_manage_projects)
def task_update_notes_view(request, pk):
    """
    Handles in-place editing of a task's text fields (client_comments or completion_notes).
    """
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        field_to_update = request.POST.get('field')
        content = request.POST.get('content')

        if field_to_update == 'client_comments':
            task.client_comments = content
            messages.success(request, 'Client comments updated successfully.')
        elif field_to_update == 'completion_notes':
            task.completion_notes = content
            messages.success(request, 'Completion notes updated successfully.')
        
        task.save(update_fields=[field_to_update])

    return redirect('task_detail', pk=task.pk)

@login_required
@user_passes_test(can_manage_projects)
def task_detail_view(request, pk):
    """
    Displays full details for a single task, including its specific comments
    and photos. Also handles the uploading of new photos for this task.
    """
    task = get_object_or_404(Task.objects.select_related('project'), pk=pk)
    
    # Handle the photo upload form submission
    if request.method == 'POST':
        photo_form = TaskPhotoForm(request.POST, request.FILES)
        if photo_form.is_valid():
            photo = photo_form.save(commit=False)
            photo.task = task
            photo.uploaded_by = request.user
            photo.save()
            messages.success(request, 'Photo has been added to the task.')
            return redirect('task_detail', pk=task.pk)
    else:
        photo_form = TaskPhotoForm()
        
    photos = task.photos.select_related('uploaded_by').all()
    context = {
        'task': task,
        'project': task.project,
        'photos': photos,
        'photo_form': photo_form,
    }
    return render(request, 'projects/task_detail.html', context)

@login_required
@user_passes_test(can_manage_projects)
def project_create_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            # If the creator is a supervisor, assign them automatically
            if request.user.role in ['supervisor1', 'supervisor2']:
                project.supervisor = request.user
            project.save()
            messages.success(request, 'Project created successfully.')
            return redirect('project_list')
    else:
        form = ProjectForm()
    return render(request, 'projects/project_form.html', {'form': form, 'title': 'Create New Project'})

@login_required
@user_passes_test(can_manage_projects)
def project_update_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, 'Project updated successfully.')
            return redirect('project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, 'projects/project_form.html', {'form': form, 'title': f'Edit Project: {project.name}'})

@login_required
@user_passes_test(is_admin_or_owner)
def project_delete_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        project.delete()
        messages.success(request, f'Project "{project.name}" deleted successfully.')
    return redirect('project_list')


@login_required
@user_passes_test(can_manage_projects)
def expense_create_view(request, project_id=None):
    initial_data = {}
    if project_id:
        initial_data['project'] = project_id

    if request.method == 'POST':
        form = ProjectExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.recorded_by = request.user
            expense.save()
            messages.success(request, 'Expense recorded successfully.')
            return redirect('project_detail', pk=expense.project.id)
    else:
        form = ProjectExpenseForm(initial=initial_data)

    if not is_admin_or_owner(request.user):
        form.fields['project'].queryset = Project.objects.filter(supervisor=request.user)

    return render(request, 'projects/expense_form.html', {'form': form, 'title': 'Add New Expense'})

@login_required
@user_passes_test(can_manage_projects)
def expense_list_view(request, project_pk):
    """
    Displays a full list of all expenses for a single project.
    """
    project = get_object_or_404(Project, pk=project_pk)
    expenses = project.expenses.select_related('recorded_by').all()
    context = {
        'project': project,
        'expenses': expenses,
    }
    return render(request, 'projects/expense_list.html', context)

@login_required
@user_passes_test(can_add_attendance)
def project_photos_view(request, pk):
    """
    Displays a gallery of photos for a project and handles new uploads.
    """
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.project = project
            photo.uploaded_by = request.user
            photo.save()
            messages.success(request, 'Photo uploaded successfully.')
            return redirect('project_photos', pk=project.pk)
    else:
        form = ProjectPhotoForm()

    photos = project.photos.all()
    context = {
        'project': project,
        'photos': photos,
        'form': form,
    }
    return render(request, 'projects/project_photos.html', context)

@login_required
@user_passes_test(is_admin_or_owner)
def document_delete_view(request, pk):
    """
    Handles the deletion of a single project document.
    """
    document = get_object_or_404(ProjectDocument, pk=pk)
    project_pk = document.project.pk
    
    if request.method == 'POST':
        document.delete()
        messages.success(request, f'Document "{document.title}" has been deleted.')
        
    # Redirect back to the project detail page, ensuring the 'documents' tab is active.
    redirect_url = f"{reverse('project_detail', kwargs={'pk': project_pk})}?tab=documents"
    return redirect(redirect_url)



