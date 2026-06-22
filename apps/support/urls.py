from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('chat/', views.chat_home, name='chat_home'),
    path('chat/<int:room_id>/', views.chat_room_view, name='chat_room_view'),
    path('chat/<int:room_id>/upload/', views.upload_chat_file, name='upload_chat_file'),
    path('dashboard/', views.support_dashboard, name='support_dashboard'),
    path('export/tickets/', views.export_tickets_csv, name='export_tickets_csv'),
    path('export/agents/', views.export_agents_csv, name='export_agents_csv'),
]
