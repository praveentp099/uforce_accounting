from django.urls import path
from . import views

urlpatterns = [
    path('', views.worker_list_view, name='worker_list'),
    path('create/', views.worker_create_view, name='worker_create'),
    path('<int:pk>/update/', views.worker_update_view, name='worker_update'),
    path('<int:pk>/toggle-active/', views.worker_toggle_active_view, name='worker_toggle_active'),
    path('attendance/<int:pk>/', views.worker_detail_view, name='worker_attendance_detail'), 

    path('attendance/', views.attendance_list_view, name='attendance_list'),
    path('attendance/create/', views.attendance_create_view, name='attendance_create'),
    path('<int:project_id>/attendance/create/', views.attendance_create_view, name='attendance_create_for_project'),
]
