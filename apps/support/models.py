from django.db import models
from django.conf import settings
import uuid

class SupportAgent(models.Model):
    DEPARTMENT_CHOICES = (
        ('technical', 'Technical Support'),
        ('academic', 'Academic Support'),
        ('billing', 'Billing & Payment'),
        ('general', 'General Query'),
    )
    STATUS_CHOICES = (
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('busy', 'Busy'),
    )
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_agent_profile')
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES, default='general')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')

    def __str__(self):
        return f"Support Agent: {self.user.username} ({self.get_department_display()})"

class SupportTicket(models.Model):
    CATEGORY_CHOICES = (
        ('technical', 'Technical Issue'),
        ('course_access', 'Course Access Issue'),
        ('payment', 'Payment Issue'),
        ('assignment', 'Assignment Issue'),
        ('general', 'General Query'),
    )
    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )

    ticket_id = models.CharField(max_length=20, unique=True, blank=True)
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='support_tickets')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    subject = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    attachment = models.FileField(upload_to='support/tickets/', blank=True, null=True)
    assigned_to = models.ForeignKey(SupportAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_id:
            self.ticket_id = f"TKT-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ticket_id} - {self.subject} ({self.get_status_display()})"

class ChatRoom(models.Model):
    student = models.ForeignKey('accounts.Student', on_delete=models.CASCADE, related_name='chat_rooms')
    support_agent = models.ForeignKey(SupportAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_rooms')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        agent_name = self.support_agent.user.username if self.support_agent else "Unassigned"
        return f"Chat: {self.student.user.username} with {agent_name}"

class Message(models.Model):
    chatroom = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_support_messages')
    message = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='support/chats/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Msg from {self.sender.username} at {self.timestamp}"

class SupportNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Support Notification for {self.user.username}: {self.title}"

class TicketReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    attachment = models.FileField(upload_to='support/tickets/replies/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.sender.username} on ticket {self.ticket.ticket_id}"
