from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/update/', views.user_update_view, name='user_update'),
    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),
    path('list/', views.account_list_view, name='account_list'),
    path('add/', views.account_create_view, name='account_add'),
    path('<int:pk>/edit/', views.account_update_view, name='account_edit'),
    path('payables/', views.payable_list_view, name='payable_list'),
    path('payables/mark-paid/<int:pk>/', views.mark_attendance_paid_view, name='mark_attendance_paid'),
    path('payables/group/<int:group_id>/', views.group_payment_detail_view, name='group_payment_detail'),
    
    # This is the URL for the selected view function
    path('payables/group/<int:group_id>/pay/', views.group_pay_all_view, name='group_pay_all'),
    path('materials/', views.material_list_view, name='material_list'),
    path('materials/create/', views.material_create_view, name='material_create'),
    path('materials/<int:pk>/update/', views.material_update_view, name='material_update'),
    path('materials/<int:pk>/delete/', views.material_delete_view, name='material_delete'),
    # Invoice URLs
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('invoices/create/', views.invoice_create_view, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail_view, name='invoice_detail'),
    path('invoices/<int:pk>/update/', views.invoice_update_view, name='invoice_update'),
]
