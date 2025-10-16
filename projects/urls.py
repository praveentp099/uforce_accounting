from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list_view, name='project_list'),
    path('create/', views.project_create_view, name='project_add'),
    path('<int:pk>/', views.project_detail_view, name='project_detail'),
    path('<int:pk>/update/', views.project_update_view, name='project_edit'),
    path('<int:pk>/delete/', views.project_delete_view, name='project_delete'),
    path('tasks/<int:pk>/toggle/', views.task_toggle_status_view, name='task_toggle_status'),
    path('expenses/create/', views.expense_create_view, name='expense_create'),
    path('tasks/<int:pk>/update/', views.task_update_view, name='task_update'),
    path('tasks/<int:pk>/', views.task_detail_view, name='task_detail'),
    path('<int:project_id>/expenses/create/', views.expense_create_view, name='expense_create_for_project'),
    path('<int:pk>/photos/', views.project_photos_view, name='project_photos'),
    path('tasks/<int:pk>/update-notes/', views.task_update_notes_view, name='task_update_notes'),
    path('documents/<int:pk>/delete/', views.document_delete_view, name='document_delete'),
    path('<int:project_pk>/expenses/', views.expense_list_view, name='expense_list'),

]
