from django.db import models
from django.conf import settings
from decimal import Decimal
from datetime import datetime, time, date, timedelta

class OutsourcedGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    leader = models.ForeignKey(
        'Worker',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='led_group',
        limit_choices_to={'worker_type': 'outsourced'}
    )

    def __str__(self):
        return self.name

class Worker(models.Model):
    WORKER_TYPES = (
        ('own', 'Own Worker'),
        ('outsourced', 'Outsourced Worker'),
    )
    name = models.CharField(max_length=100)
    worker_type = models.CharField(max_length=20, choices=WORKER_TYPES)
    group = models.ForeignKey(
        OutsourcedGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members'
    )
    fixed_wage = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Monthly salary for 'Own' workers.")
    daily_wage = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Daily wage for 'Outsourced' workers.")
    contact = models.CharField(max_length=15, blank=True)
    ot1_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="OT1 Rate", help_text="Overtime rate per hour for normal days.")
    ot2_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="OT2 Rate", help_text="Overtime rate per hour for holidays.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_worker_type_display()})"

class WorkerAttendance(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='attendances')
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    
    # New Time Fields
    in_time = models.TimeField()
    out_time = models.TimeField()
    is_holiday = models.BooleanField(default=False, verbose_name="Mark as Holiday Attendance")
    is_paid = models.BooleanField(default=False, help_text="Mark this record as paid.") # Using boolean field

    # Calculated Fields (Read-only)
    hours_worked = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0, editable=False)
    total_wage = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)
    
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Worker Attendances"
        unique_together = ['worker', 'date']
        ordering = ['-date']

    def calculate_hours_and_wage(self):
        """Calculates total hours, overtime, and wage based on in/out times."""
        start_dt = datetime.combine(self.date, self.in_time)
        end_dt = datetime.combine(self.date, self.out_time)
        
        duration = end_dt - start_dt if end_dt > start_dt else timedelta()
        total_hours = Decimal(duration.total_seconds() / 3600)
        self.hours_worked = total_hours

        standard_hours = Decimal(getattr(settings, 'STANDARD_WORK_HOURS_PER_DAY', 8))

        if self.is_holiday:
            self.overtime_hours = total_hours
            self.total_wage = total_hours * self.worker.ot2_rate
        else:
            regular_hours = min(total_hours, standard_hours)
            ot_hours = max(total_hours - standard_hours, Decimal(0))
            self.overtime_hours = ot_hours

            if self.worker.worker_type == 'own':
                work_days_per_month = Decimal(getattr(settings, 'WORK_DAYS_PER_MONTH', 30))
                if work_days_per_month > 0 and standard_hours > 0:
                    hourly_rate = (self.worker.fixed_wage / work_days_per_month) / standard_hours
                    regular_wage = regular_hours * hourly_rate
                    overtime_wage = ot_hours * self.worker.ot1_rate
                    self.total_wage = regular_wage + overtime_wage
                else:
                    self.total_wage = 0
            else: # Outsourced
                overtime_wage = ot_hours * self.worker.ot1_rate
                self.total_wage = self.worker.daily_wage + overtime_wage

    def save(self, *args, **kwargs):
        self.calculate_hours_and_wage()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.worker.name} on {self.date}"

