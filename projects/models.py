from django.db import models
from django.conf import settings
from django.db.models import Q, Sum
from django.utils import timezone
from django.urls import reverse 
from workers.models import WorkerAttendance
from accounts.models import Supplier

class ProjectManager(models.Manager):
    """
    Custom manager for the Project model to handle role-based filtering.
    """
    def filter_for_user(self, user):
        if user.role in ['admin', 'owner']:
            return self.all()
        elif user.role == 'supervisor':
            return self.filter(supervisor=user)
        elif user.role == 'foreman':
            return self.filter(status='active')
        return self.none()

class Project(models.Model):
    PRIORITY_CHOICES = (('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('very_high', 'Very High'))
    STATUS_CHOICES = (('active', 'Active'), ('completed', 'Completed'), ('on_hold', 'On Hold'))

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0, editable=False)
    
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role': 'supervisor'}
    )
    
    client_company = models.CharField(max_length=200, blank=True, verbose_name="Client Company")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    progress = models.IntegerField(default=0, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    client_comments = models.TextField(blank=True, verbose_name="Client Comments")
    remarks = models.TextField(blank=True, verbose_name="Internal Remarks")
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    objects = ProjectManager()

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """
        Returns the canonical URL for a project instance.
        This is the method that was missing.
        """
        return reverse('project_detail', kwargs={'pk': self.pk})

    def update_progress(self):
        """
        Calculates the project progress based on the ratio of completed tasks.
        """
        tasks = self.tasks.all()
        total_tasks = tasks.count()
        if total_tasks > 0:
            completed_tasks = tasks.filter(status='completed').count()
            self.progress = int((completed_tasks / total_tasks) * 100)
        else:
            self.progress = 0
        self.save(update_fields=['progress'])

    def update_actual_cost(self):
        """
        Calculates the total actual cost of the project by summing all related
        expenses and worker wages.
        """
        expense_total = self.expenses.aggregate(total=Sum('amount'))['total'] or 0
        wage_total = self.attendances.aggregate(total=Sum('total_wage'))['total'] or 0
        self.actual_cost = expense_total + wage_total
        self.save(update_fields=['actual_cost'])


class Task(models.Model):
    STATUS_CHOICES = (
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    )
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    
    # New field for task-specific client comments
    client_comments = models.TextField(blank=True, help_text="Client feedback specific to this task.")
    
    completion_notes = models.TextField(blank=True, help_text="Reason if the task was not completed on the due date.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['due_date', 'created_at']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        if self.due_date and self.due_date < timezone.now().date() and self.status != 'completed':
            return True
        return False

class TaskPhoto(models.Model):
    """
    Represents a single photo uploaded for a specific task.
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='task_photos/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Photo for task '{self.task.title}'"
    
class ProjectDocument(models.Model):
    """
    Represents a single document (e.g., PDF) uploaded for a project.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='project_documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class ProjectExpense(models.Model):
    """
    Represents a non-wage expense related to a project, now with supplier tracking.
    """
    EXPENSE_TYPES = (
        ('materials', 'Materials'),
        ('vehicle_rent', 'Vehicle Rent'),
        ('equipment_rent', 'Equipment Rent'),
        ('food_beverages', 'Food & Beverages'),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=50, choices=EXPENSE_TYPES)
    
    # This field now links to the new Supplier model
    supplier = models.ForeignKey(
        'accounts.Supplier',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Supplier/Shop"
    )
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.get_expense_type_display()} for {self.project.name}"




class ProjectPhoto(models.Model):
    """
    Represents a single photo uploaded for a project on a specific day.
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='project_photos/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(default=timezone.now)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Photo for {self.project.name} on {self.date}"