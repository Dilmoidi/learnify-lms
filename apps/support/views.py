from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.utils import timezone
from .models import SupportTicket, SupportAgent, TicketReply, SupportNotification, ChatRoom
from .forms import SupportTicketForm, TicketReplyForm, TicketStatusAssignForm
from apps.accounts.models import Student
from apps.notifications.models import Notification

def send_notifications(user, title, message_text):
    # 1. Create support app notification
    SupportNotification.objects.create(user=user, title=title, message=message_text)
    # 2. Create global notifications for navbar integration
    Notification.objects.create(user=user, message=f"💬 {title}: {message_text[:60]}")

@login_required
def ticket_list(request):
    user = request.user
    is_agent = hasattr(user, 'support_agent_profile')
    is_admin = user.role == 'admin' or user.is_superuser

    if is_agent or is_admin:
        # Support agents and admins see all tickets
        tickets = SupportTicket.objects.select_related('student__user', 'assigned_to__user').all()
        open_count = tickets.filter(status='open').count()
        in_progress_count = tickets.filter(status='in_progress').count()
        resolved_count = tickets.filter(status='resolved').count()
        
        context = {
            'tickets': tickets,
            'open_count': open_count,
            'in_progress_count': in_progress_count,
            'resolved_count': resolved_count,
        }
        template = 'support/agent_ticket_list.html'
    else:
        # Students see their own tickets
        if not hasattr(user, 'student_profile'):
            messages.error(request, "Only students can view their support tickets.")
            return redirect('dashboard')
        tickets = SupportTicket.objects.filter(student=user.student_profile).select_related('assigned_to__user')
        context = {'tickets': tickets}
        template = 'support/student_ticket_list.html'

    return render(request, template, context)

@login_required
def ticket_create(request):
    user = request.user
    if user.role != 'student' or not hasattr(user, 'student_profile'):
        messages.error(request, "Only students can raise support tickets.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = SupportTicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.student = user.student_profile
            ticket.save()

            # Notify admins/agents
            agent_users = SupportAgent.objects.select_related('user').all()
            for agent in agent_users:
                send_notifications(
                    user=agent.user,
                    title="New Support Ticket Raised",
                    message_text=f"Student {user.username} raised ticket {ticket.ticket_id}: '{ticket.subject}'"
                )

            messages.success(request, f"Support ticket {ticket.ticket_id} created successfully.")
            return redirect('support:ticket_list')
    else:
        form = SupportTicketForm()

    return render(request, 'support/ticket_create.html', {'form': form})

@login_required
def ticket_detail(request, ticket_id):
    user = request.user
    ticket = get_object_or_404(SupportTicket.objects.select_related('student__user', 'assigned_to__user'), ticket_id=ticket_id)

    # Check permission
    is_student_owner = hasattr(user, 'student_profile') and ticket.student == user.student_profile
    is_agent = hasattr(user, 'support_agent_profile')
    is_admin = user.role == 'admin' or user.is_superuser

    if not (is_student_owner or is_agent or is_admin):
        return HttpResponseForbidden("You do not have permission to view this ticket.")

    replies = ticket.replies.select_related('sender').all()

    if request.method == 'POST':
        # Check if form is for reply or status change
        if 'btn_reply' in request.POST:
            reply_form = TicketReplyForm(request.POST, request.FILES)
            status_form = TicketStatusAssignForm(instance=ticket)
            if reply_form.is_valid():
                reply = reply_form.save(commit=False)
                reply.ticket = ticket
                reply.sender = user
                reply.save()

                # Automatically update status to 'in_progress' if an agent replies
                if is_agent or is_admin:
                    if ticket.status == 'open':
                        ticket.status = 'in_progress'
                        ticket.save()

                # Dispatch notifications
                if is_student_owner:
                    if ticket.assigned_to:
                        send_notifications(
                            user=ticket.assigned_to.user,
                            title="Ticket Reply Received",
                            message_text=f"Student {user.username} replied on ticket {ticket.ticket_id}."
                        )
                else:
                    send_notifications(
                        user=ticket.student.user,
                        title="Agent Response on Ticket",
                        message_text=f"Agent {user.username} replied to your support ticket {ticket.ticket_id}."
                    )

                messages.success(request, "Reply added successfully.")
                return redirect('support:ticket_detail', ticket_id=ticket.ticket_id)
        elif 'btn_update_status' in request.POST and (is_agent or is_admin):
            status_form = TicketStatusAssignForm(request.POST, instance=ticket)
            reply_form = TicketReplyForm()
            if status_form.is_valid():
                old_status = ticket.status
                old_agent = ticket.assigned_to
                ticket = status_form.save()

                # Notification for assignment
                if ticket.assigned_to and ticket.assigned_to != old_agent:
                    send_notifications(
                        user=ticket.assigned_to.user,
                        title="New Support Ticket Assigned",
                        message_text=f"Support ticket {ticket.ticket_id} has been assigned to you."
                    )
                    send_notifications(
                        user=ticket.student.user,
                        title="Support Ticket Agent Assigned",
                        message_text=f"Agent {ticket.assigned_to.user.username} has been assigned to support ticket {ticket.ticket_id}."
                    )

                # Notification for status change
                if ticket.status != old_status:
                    send_notifications(
                        user=ticket.student.user,
                        title="Support Ticket Status Updated",
                        message_text=f"Your ticket {ticket.ticket_id} status has been changed to '{ticket.get_status_display()}'."
                    )

                messages.success(request, "Ticket properties updated successfully.")
                return redirect('support:ticket_detail', ticket_id=ticket.ticket_id)
    else:
        reply_form = TicketReplyForm()
        status_form = TicketStatusAssignForm(instance=ticket)

    return render(request, 'support/ticket_detail.html', {
        'ticket': ticket,
        'replies': replies,
        'reply_form': reply_form,
        'status_form': status_form,
        'is_agent': is_agent or is_admin,
    })

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@login_required
def chat_home(request):
    user = request.user
    is_agent = hasattr(user, 'support_agent_profile')
    is_admin = user.role == 'admin' or user.is_superuser

    if is_agent or is_admin:
        # Create profile if not exist for testing convenience
        agent, _ = SupportAgent.objects.get_or_create(
            user=user,
            defaults={'department': 'general', 'status': 'online'}
        )
        
        # Load all rooms and annotate with last message info & unread message count
        rooms = ChatRoom.objects.all().select_related('student__user', 'support_agent__user')
        # Simple list of rooms
        return render(request, 'support/agent_chat_dashboard.html', {
            'rooms': rooms,
            'agent': agent
        })
    else:
        # Student: Auto-create chatroom if it doesn't exist
        if not hasattr(user, 'student_profile'):
            messages.error(request, "Only students can access chat support.")
            return redirect('dashboard')
        
        room, created = ChatRoom.objects.get_or_create(student=user.student_profile)
        return redirect('support:chat_room_view', room_id=room.id)

@login_required
def chat_room_view(request, room_id):
    user = request.user
    room = get_object_or_404(ChatRoom.objects.select_related('student__user', 'support_agent__user'), pk=room_id)

    # Permission check
    is_student_owner = hasattr(user, 'student_profile') and room.student == user.student_profile
    is_agent = hasattr(user, 'support_agent_profile')
    is_admin = user.role == 'admin' or user.is_superuser

    if not (is_student_owner or is_agent or is_admin):
        return HttpResponseForbidden("You do not have permission to access this chat room.")

    # Auto-assign agent to room if unassigned and accessed by an agent
    if (is_agent or is_admin) and not room.support_agent:
        agent = getattr(user, 'support_agent_profile', None)
        if agent:
            room.support_agent = agent
            room.save()

    # Mark messages as read
    room.messages.exclude(sender=user).update(is_read=True)

    past_messages = room.messages.select_related('sender').all()

    # Get WebSocket protocol (ws or wss depending on https)
    ws_scheme = 'wss' if request.is_secure() else 'ws'

    return render(request, 'support/chat_room.html', {
        'room': room,
        'past_messages': past_messages,
        'ws_scheme': ws_scheme,
    })

@login_required
def upload_chat_file(request, room_id):
    if request.method == 'POST' and request.FILES.get('file'):
        room = get_object_or_404(ChatRoom, pk=room_id)
        uploaded_file = request.FILES['file']
        
        # Save as message with attachment
        msg = Message.objects.create(
            chatroom=room,
            sender=request.user,
            message='',
            file=uploaded_file
        )
        
        return JsonResponse({
            'status': 'success',
            'file_url': msg.file.url,
            'file_name': uploaded_file.name,
            'timestamp': msg.timestamp.strftime('%H:%M')
        })
        
    return JsonResponse({'status': 'error', 'message': 'Invalid file upload'})

import datetime
from django.db.models import Count
import csv
from django.http import HttpResponse

@login_required
def support_dashboard(request):
    user = request.user
    is_agent = hasattr(user, 'support_agent_profile')
    is_admin = user.role == 'admin' or user.is_superuser

    if not (is_agent or is_admin):
        return HttpResponseForbidden("You do not have permission to view the support dashboard.")

    # 1. Basic Stats
    total_tickets = SupportTicket.objects.count()
    pending_tickets = SupportTicket.objects.filter(status__in=['open', 'in_progress']).count()
    resolved_tickets = SupportTicket.objects.filter(status='resolved').count()
    active_chats = ChatRoom.objects.count()

    resolution_rate = int((resolved_tickets / total_tickets) * 100) if total_tickets > 0 else 0

    # 2. Avg Response Time (minutes)
    tickets_with_replies = SupportTicket.objects.filter(status__in=['in_progress', 'resolved', 'closed'])
    total_time = datetime.timedelta()
    reply_count = 0
    for t in tickets_with_replies:
        first_reply = t.replies.exclude(sender=t.student.user).order_by('created_at').first()
        if first_reply:
            total_time += (first_reply.created_at - t.created_at)
            reply_count += 1
    avg_response_minutes = round((total_time.total_seconds() / 60 / reply_count), 1) if reply_count > 0 else 0.0

    # 3. Category Distribution (Most Common Issues)
    categories_qs = SupportTicket.objects.values('category').annotate(count=Count('id')).order_by('-count')
    category_labels = []
    category_counts = []
    category_mapping = dict(SupportTicket.CATEGORY_CHOICES)
    for cat in categories_qs:
        category_labels.append(category_mapping.get(cat['category'], cat['category']))
        category_counts.append(cat['count'])

    # 4. Support Tickets over last 7 days
    today = timezone.now().date()
    last_7_days = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    ticket_trend_counts = []
    day_labels = []
    for day in last_7_days:
        day_labels.append(day.strftime('%b %d'))
        count = SupportTicket.objects.filter(created_at__date=day).count()
        ticket_trend_counts.append(count)

    # 5. Peak Support Hours
    hour_counts = [0] * 24
    for t in SupportTicket.objects.all():
        hour_counts[t.created_at.hour] += 1
    hour_labels = [f"{i}:00" for i in range(24)]

    # 6. Agent Performance Reports
    agents_perf = []
    for agent in SupportAgent.objects.select_related('user').all():
        assigned_count = agent.assigned_tickets.count()
        resolved_count = agent.assigned_tickets.filter(status='resolved').count()
        
        agent_time = datetime.timedelta()
        agent_replies_count = 0
        for t in agent.assigned_tickets.all():
            first_reply = t.replies.filter(sender=agent.user).order_by('created_at').first()
            if first_reply:
                agent_time += (first_reply.created_at - t.created_at)
                agent_replies_count += 1
        avg_agent_time = round((agent_time.total_seconds() / 60 / agent_replies_count), 1) if agent_replies_count > 0 else 0.0
        
        agents_perf.append({
            'username': agent.user.username,
            'department': agent.get_department_display(),
            'assigned': assigned_count,
            'resolved': resolved_count,
            'avg_time': avg_agent_time,
            'status': agent.get_status_display()
        })

    # 7. Recent Activities
    activities = []
    # Recent tickets
    for t in SupportTicket.objects.select_related('student__user').order_by('-created_at')[:5]:
        activities.append({
            'icon': 'bi-plus-circle text-teal',
            'text': f"New ticket {t.ticket_id} created by student @{t.student.user.username}.",
            'time': t.created_at
        })
    # Recent ticket replies
    for r in TicketReply.objects.select_related('sender', 'ticket').order_by('-created_at')[:5]:
        role_label = 'Agent' if r.sender.role != 'student' else 'Student'
        activities.append({
            'icon': 'bi-chat-left-text text-purple-accent',
            'text': f"{role_label} @{r.sender.username} replied on ticket {r.ticket.ticket_id}.",
            'time': r.created_at
        })
    activities.sort(key=lambda x: x['time'], reverse=True)
    recent_activities = activities[:8]

    # Active chat rooms
    rooms = ChatRoom.objects.select_related('student__user').all()[:5]

    return render(request, 'support/dashboard.html', {
        'total_tickets': total_tickets,
        'pending_tickets': pending_tickets,
        'resolved_tickets': resolved_tickets,
        'active_chats': active_chats,
        'resolution_rate': resolution_rate,
        'avg_response_minutes': avg_response_minutes,
        
        # Charts data
        'category_labels': category_labels,
        'category_counts': category_counts,
        'day_labels': day_labels,
        'ticket_trend_counts': ticket_trend_counts,
        'hour_labels': hour_labels,
        'hour_counts': hour_counts,
        
        # Agents & Activities
        'agents_perf': agents_perf,
        'recent_activities': recent_activities,
        'rooms': rooms,
        'is_admin': is_admin
    })

@login_required
def export_tickets_csv(request):
    if not (hasattr(request.user, 'support_agent_profile') or request.user.role == 'admin' or request.user.is_superuser):
        return HttpResponseForbidden("Unauthorized")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="support_tickets_report_{datetime.date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ticket ID', 'Student', 'Category', 'Subject', 'Priority', 'Status', 'Assigned Agent', 'Created Date', 'Last Updated'])

    tickets = SupportTicket.objects.select_related('student__user', 'assigned_to__user').all()
    for t in tickets:
        agent_name = t.assigned_to.user.username if t.assigned_to else 'Unassigned'
        writer.writerow([
            t.ticket_id,
            t.student.user.username,
            t.get_category_display(),
            t.subject,
            t.get_priority_display(),
            t.get_status_display(),
            agent_name,
            t.created_at.strftime('%Y-%m-%d %H:%M'),
            t.updated_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response

@login_required
def export_agents_csv(request):
    if not (request.user.role == 'admin' or request.user.is_superuser):
        return HttpResponseForbidden("Unauthorized")

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="support_agents_performance_{datetime.date.today()}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Agent Username', 'Department', 'Assigned Tickets', 'Resolved Tickets', 'Avg Response Time (min)', 'Current Status'])

    for agent in SupportAgent.objects.select_related('user').all():
        assigned_count = agent.assigned_tickets.count()
        resolved_count = agent.assigned_tickets.filter(status='resolved').count()
        
        agent_time = datetime.timedelta()
        agent_replies_count = 0
        for t in agent.assigned_tickets.all():
            first_reply = t.replies.filter(sender=agent.user).order_by('created_at').first()
            if first_reply:
                agent_time += (first_reply.created_at - t.created_at)
                agent_replies_count += 1
        avg_agent_time = round((agent_time.total_seconds() / 60 / agent_replies_count), 1) if agent_replies_count > 0 else 0.0
        
        writer.writerow([
            agent.user.username,
            agent.get_department_display(),
            assigned_count,
            resolved_count,
            avg_agent_time,
            agent.get_status_display()
        ])

    return response
