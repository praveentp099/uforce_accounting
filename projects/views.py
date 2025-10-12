from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Project, ProjectExpense, Task
from .forms import ProjectForm, ProjectExpenseForm, TaskForm, TaskUpdateForm, ProjectPhotoForm
from accounts.views import is_admin_or_owner, can_manage_projects, can_add_attendance
from django.db.models import Sum

@login_required
def project_list_view(request):
    """
    Displays a list of projects visible to the current user.
    """
    projects = Project.objects.filter_for_user(request.user).select_related('supervisor')
    return render(request, 'projects/project_list.html', {'projects': projects})

@login_required
@user_passes_test(can_manage_projects)
def project_detail_view(request, pk):
    """
    Displays the main dashboard for a single project, including its tasks,
    and handles the creation of new tasks.
    """
    project = get_object_or_404(Project.objects.select_related('supervisor'), pk=pk)
    
    # Handle the "Add Task" form submission
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

    tasks = project.tasks.all()
    context = {
        'project': project,
        'tasks': tasks,
        'task_form': task_form,
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