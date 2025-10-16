from django.urls import path
from . import views

urlpatterns = [
    path('', views.quotation_list_view, name='quotation_list'),
    path('upload/', views.quotation_create_view, name='quotation_create'),
    path('<int:pk>/status/<str:status>/', views.quotation_update_status_view, name='quotation_update_status'),
]
