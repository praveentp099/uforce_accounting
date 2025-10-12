from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts import views as account_views
from accounts.views import dashboard_view

urlpatterns = [

    
    path('admin/', admin.site.urls),
    path('', dashboard_view, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', account_views.logout_view, name='logout'),    path('accounts/', include('accounts.urls')),
    path('workers/', include('workers.urls')),
    path('projects/', include('projects.urls')),
    path('reports/', include('reports.urls')),
    

]