import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import ChatRoom, Message, SupportAgent

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group_name = f"chat_room_{self.room_id}"

        # Reject unauthenticated connections
        if not self.user.is_authenticated:
            await self.close()
            return

        # Check access permission to room
        has_access = await self.check_room_access(self.room_id, self.user)
        if not has_access:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Mark messages in this room as read for the user
        await self.mark_messages_as_read(self.room_id, self.user)

        # Broadcast online status
        await self.broadcast_user_status(True)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # Broadcast offline status
        await self.broadcast_user_status(False)

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'chat_message':
            message_text = data.get('message', '')
            file_url = data.get('file_url', None)
            file_name = data.get('file_name', None)

            # Enforce 100 character length limit
            if message_text:
                message_text = message_text[:100]

            # Save message to database
            msg = await self.save_message(self.room_id, self.user, message_text, file_url)

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message_event',
                    'message': msg['message'],
                    'sender': msg['sender'],
                    'sender_id': msg['sender_id'],
                    'file_url': msg['file_url'],
                    'file_name': file_name,
                    'timestamp': msg['timestamp']
                }
            )

        elif action == 'typing':
            is_typing = data.get('typing', False)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_event',
                    'sender': self.user.username,
                    'sender_id': self.user.id,
                    'typing': is_typing
                }
            )

    # Receive message from room group
    async def chat_message_event(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'action': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'file_url': event['file_url'],
            'file_name': event['file_name'],
            'timestamp': event['timestamp']
        }))

    # Receive typing status from room group
    async def typing_event(self, event):
        await self.send(text_data=json.dumps({
            'action': 'typing',
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'typing': event['typing']
        }))

    # Receive user status update from room group
    async def status_event(self, event):
        await self.send(text_data=json.dumps({
            'action': 'status',
            'username': event['username'],
            'user_id': event['user_id'],
            'online': event['online']
        }))

    # Helper method to broadcast status
    async def broadcast_user_status(self, is_online):
        # If user is a support agent, update status in DB
        if is_online:
            await self.update_agent_db_status(self.user, 'online')
        else:
            await self.update_agent_db_status(self.user, 'offline')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'status_event',
                'username': self.user.username,
                'user_id': self.user.id,
                'online': is_online
            }
        )

    # Database Sync Helpers
    @database_sync_to_async
    def check_room_access(self, room_id, user):
        try:
            room = ChatRoom.objects.get(pk=room_id)
            is_student_owner = hasattr(user, 'student_profile') and room.student == user.student_profile
            is_agent = hasattr(user, 'support_agent_profile')
            is_admin = user.role == 'admin' or user.is_superuser
            return is_student_owner or is_agent or is_admin
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, room_id, user, message_text, file_url=None):
        room = ChatRoom.objects.get(pk=room_id)
        msg = Message.objects.create(
            chatroom=room,
            sender=user,
            message=message_text,
            file=file_url
        )
        return {
            'message': msg.message,
            'sender': msg.sender.username,
            'sender_id': msg.sender.id,
            'file_url': msg.file.url if msg.file else None,
            'timestamp': msg.timestamp.strftime('%H:%M')
        }

    @database_sync_to_async
    def mark_messages_as_read(self, room_id, user):
        Message.objects.filter(chatroom_id=room_id).exclude(sender=user).update(is_read=True)

    @database_sync_to_async
    def update_agent_db_status(self, user, status_val):
        if hasattr(user, 'support_agent_profile'):
            agent = user.support_agent_profile
            agent.status = status_val
            agent.save()
