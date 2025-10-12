from django.contrib import admin
from .models import Project, ProjectExpense

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'budget', 'actual_cost', 'status', 'supervisor')
    list_filter = ('status', 'start_date')
    search_fields = ('name', 'description')

@admin.register(ProjectExpense)
class ProjectExpenseAdmin(admin.ModelAdmin):
    list_display = ('project', 'expense_type', 'amount', 'date', 'recorded_by')
    list_filter = ('expense_type', 'date')
    search_fields = ('project__name', 'description')