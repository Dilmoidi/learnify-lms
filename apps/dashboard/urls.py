from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard'),
    path('admin/export/courses/', views.admin_export_courses_csv, name='admin_export_courses_csv'),
    path('admin/export/users/', views.admin_export_users_csv, name='admin_export_users_csv'),
    path('admin/export/instructors/', views.admin_export_instructors_csv, name='admin_export_instructors_csv'),
]
