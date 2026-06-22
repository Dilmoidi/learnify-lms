from django.contrib import admin
from .models import SupportAgent, SupportTicket, ChatRoom, Message, SupportNotification, TicketReply

@admin.register(TicketReply)
class TicketReplyAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'sender', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('sender__username', 'message', 'ticket__ticket_id')

@admin.register(SupportAgent)
class SupportAgentAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'status')
    list_filter = ('department', 'status')
    search_fields = ('user__username', 'user__email')

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'student', 'category', 'priority', 'status', 'assigned_to', 'created_at')
    list_filter = ('category', 'priority', 'status', 'assigned_to')
    search_fields = ('ticket_id', 'subject', 'description', 'student__user__username')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('student', 'support_agent', 'created_at')
    list_filter = ('support_agent',)
    search_fields = ('student__user__username', 'support_agent__user__username')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('chatroom', 'sender', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('sender__username', 'message')

@admin.register(SupportNotification)
class SupportNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
