from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_analysis_view, name='reports_dashboard'),
    path('expenses/', views.expense_report_view, name='expense_report'),
    path('balance-sheet/', views.balance_sheet_view, name='balance_sheet'),
]
