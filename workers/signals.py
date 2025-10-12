from django.apps import AppConfig
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import WorkerAttendance
class WorkersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workers'

    def ready(self):
        import workers.signals



@receiver([post_save, post_delete], sender=WorkerAttendance)
def update_project_cost_on_attendance_change(sender, instance, **kwargs):
    """
    Updates the project's actual_cost whenever attendance is saved or deleted.
    """
    if instance.project:
        instance.project.update_actual_cost()
