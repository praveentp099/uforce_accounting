from django.contrib import admin
from .models import Worker, WorkerAttendance, OutsourcedGroup

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'worker_type', 
        'group', 
        'daily_wage', 
        'fixed_wage', 
        'ot1_rate',  # Replaced 'overtime_rate' with the new fields
        'ot2_rate', 
        'is_active'
    )
    list_filter = ('worker_type', 'is_active', 'group')
    search_fields = ('name', 'contact')
    ordering = ('name',)

@admin.register(WorkerAttendance)
class WorkerAttendanceAdmin(admin.ModelAdmin):
    list_display = ('worker', 'project', 'date', 'in_time', 'out_time', 'total_wage', 'is_paid', 'is_holiday')
    list_filter = ('date', 'project', 'worker', 'is_paid', 'is_holiday')
    search_fields = ('worker__name', 'project__name')
    ordering = ('-date',)

@admin.register(OutsourcedGroup)
class OutsourcedGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'leader')
    search_fields = ('name', 'leader__name')
    autocomplete_fields = ['leader']
