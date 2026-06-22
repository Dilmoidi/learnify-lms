from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('approvals/', views.AdminApprovalsView.as_view(), name='admin_approvals'),
    path('approvals/<int:pk>/approve/', views.approve_instructor, name='approve_instructor'),
]
