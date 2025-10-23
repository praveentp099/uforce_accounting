from django.urls import path
from . import views

urlpatterns = [
    path('', views.quotation_list_view, name='quotation_list'),
    path('upload/', views.quotation_create_view, name='quotation_create'),
    path('<int:pk>/', views.quotation_detail_view, name='quotation_detail'),
    path('<int:pk>/status/<str:status>/', views.quotation_update_status_view, name='quotation_update_status'),
    path('<int:quotation_pk>/approve-file/<int:file_pk>/', views.quotation_approve_file_view, name='quotation_approve_file'),
    path('<int:pk>/reject/', views.quotation_reject_view, name='quotation_reject'),
]
