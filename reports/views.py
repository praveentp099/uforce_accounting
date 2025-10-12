from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from projects.models import Project, ProjectExpense
from workers.models import WorkerAttendance
from accounts.models import Account
from django.db.models import Sum, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from datetime import datetime, timedelta
from calendar import month_name
from collections import defaultdict
from datetime import date, timedelta
import json

@login_required
def reports_dashboard_view(request):
    # This can be a hub for all reports
    return render(request, 'reports/expense_analysis.html')

@login_required
def expense_analysis_view(request):
    """
    Handles the logic for the Expense & Wage Analysis report, including
    date range filtering.
    """
    today = date.today()
    # Default to the last 30 days if no dates are provided
    default_start_date = today - timedelta(days=29)
    
    # Get date range from GET parameters, or use defaults
    start_date_str = request.GET.get('start_date', default_start_date.strftime('%Y-%m-%d'))
    end_date_str = request.GET.get('end_date', today.strftime('%Y-%m-%d'))
    
    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    # Filter the main querysets based on the selected date range
    expenses = ProjectExpense.objects.filter(date__range=[start_date, end_date])
    attendances = WorkerAttendance.objects.filter(date__range=[start_date, end_date])

    # --- Chart Data Calculation ---
    daily_expenses_qs = expenses.values('date').annotate(total=Sum('amount')).order_by('date')
    daily_wages_qs = attendances.values('date').annotate(total=Sum('total_wage')).order_by('date')

    # Combine data in Python for a continuous chart
    chart_data = defaultdict(lambda: {'expenses': 0, 'wages': 0})
    current_date = start_date
    while current_date <= end_date:
        chart_data[current_date.strftime('%b %d')] # Ensure all dates in range are present
        current_date += timedelta(days=1)

    for item in daily_expenses_qs:
        chart_data[item['date'].strftime('%b %d')]['expenses'] = float(item['total'])
    for item in daily_wages_qs:
        chart_data[item['date'].strftime('%b %d')]['wages'] = float(item['total'])
    
    sorted_chart_data = sorted(chart_data.items(), key=lambda x: datetime.strptime(f"{x[0]} {today.year}", "%b %d %Y"))

    # --- Top Categories Calculation ---
    top_categories_qs = expenses.values('expense_type').annotate(total=Sum('amount')).order_by('-total')[:5]
    expense_type_map = dict(ProjectExpense.EXPENSE_TYPES)
    top_categories = [{'name': expense_type_map.get(cat['expense_type']), 'total': cat['total']} for cat in top_categories_qs]

    # --- Top Projects Calculation (Expenses + Wages) ---
    project_costs = defaultdict(float)
    for item in expenses.values('project__name').annotate(total=Sum('amount')):
        if item['project__name']: project_costs[item['project__name']] += float(item['total'])
    for item in attendances.values('project__name').annotate(total=Sum('total_wage')):
        if item['project__name']: project_costs[item['project__name']] += float(item['total'])
    
    top_projects = sorted(project_costs.items(), key=lambda x: x[1], reverse=True)[:5]

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'chart_labels': json.dumps([item[0] for item in sorted_chart_data]),
        'chart_expense_values': json.dumps([item[1]['expenses'] for item in sorted_chart_data]),
        'chart_wage_values': json.dumps([item[1]['wages'] for item in sorted_chart_data]),
        'top_categories': top_categories,
        'top_projects': top_projects,
    }
    return render(request, 'reports/expense_analysis.html', context)



@login_required
def expense_report_view(request):
    # Get query parameters
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    # Default to last 30 days if no dates are provided
    if not end_date_str:
        end_date = datetime.today().date()
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    if not start_date_str:
        start_date = end_date - timedelta(days=29)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()


    # Base Querysets
    expenses = ProjectExpense.objects.filter(date__range=[start_date, end_date])
    wages = WorkerAttendance.objects.filter(date__range=[start_date, end_date])

    # Top expense categories
    top_categories = expenses.values('expense_type').annotate(
        total=Sum('amount')
    ).order_by('-total')

    # Projects with highest expenses
    expensive_projects = Project.objects.filter(expenses__in=expenses).distinct().annotate(
        total_project_expenses=Sum('expenses__amount')
    ).order_by('-total_project_expenses')[:10]

    # Daily breakdown (optimized)
    daily_expense_data = expenses.annotate(day=TruncDay('date')).values('day').annotate(total=Sum('amount')).order_by('day')
    daily_wage_data = wages.annotate(day=TruncDay('date')).values('day').annotate(total=Sum('total_wage')).order_by('day')
    
    # Process for charting
    chart_labels = [(start_date + timedelta(days=i)).strftime('%b %d') for i in range((end_date - start_date).days + 1)]
    chart_expense_values = [0] * len(chart_labels)
    chart_wage_values = [0] * len(chart_labels)

    for item in daily_expense_data:
        try:
            idx = (item['day'].date() - start_date).days
            chart_expense_values[idx] = item['total']
        except IndexError:
            pass

    for item in daily_wage_data:
        try:
            idx = (item['day'].date() - start_date).days
            chart_wage_values[idx] = item['total']
        except IndexError:
            pass

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'top_categories': top_categories,
        'expensive_projects': expensive_projects,
        'total_expenses': expenses.aggregate(total=Sum('amount'))['total'] or 0,
        'total_wages': wages.aggregate(total=Sum('total_wage'))['total'] or 0,
        'chart_labels': chart_labels,
        'chart_expense_values': chart_expense_values,
        'chart_wage_values': chart_wage_values,
    }
    return render(request, 'reports/expense_report.html', context)


@login_required
def balance_sheet_view(request):
    # This is a simplified balance sheet based on account balances
    assets = Account.objects.filter(account_type='asset').order_by('name')
    liabilities = Account.objects.filter(account_type='liability').order_by('name')
    equity = Account.objects.filter(account_type='equity').order_by('name')

    total_assets = assets.aggregate(total=Sum('balance'))['total'] or 0
    total_liabilities = liabilities.aggregate(total=Sum('balance'))['total'] or 0
    total_equity = equity.aggregate(total=Sum('balance'))['total'] or 0

    context = {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'total_liabilities_and_equity': total_liabilities + total_equity,
    }
    return render(request, 'reports/balance_sheet.html', context)
