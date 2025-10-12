from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import ProjectExpense,Task
from workers.models import WorkerAttendance


@receiver([post_save, post_delete], sender=Task)
def update_project_progress_on_task_change(sender, instance, **kwargs):
    """
    When a Task is saved or deleted, this signal triggers the progress
    recalculation on its parent Project.
    """
    if instance.project:
        instance.project.update_progress()

@receiver([post_save, post_delete], sender=ProjectExpense)
def update_project_cost_on_expense_change(sender, instance, **kwargs):
    """
    When a ProjectExpense is saved or deleted, this signal triggers the
    actual_cost recalculation on its parent Project.
    """
    if instance.project:
        instance.project.update_actual_cost()

@receiver([post_save, post_delete], sender=WorkerAttendance)
def update_project_cost_on_attendance_change(sender, instance, **kwargs):
    """
    When a WorkerAttendance record is saved or deleted, this signal triggers
    the actual_cost recalculation on its related Project.
    """
    if instance.project:
        instance.project.update_actual_cost()



class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'

    def ready(self):
        import projects.signals



@receiver([post_save, post_delete], sender=ProjectExpense)
def update_project_cost_on_expense_change(sender, instance, **kwargs):
    """
    Updates the project's actual_cost whenever an expense is saved or deleted.
    """
    if instance.project:
        instance.project.update_actual_cost()
