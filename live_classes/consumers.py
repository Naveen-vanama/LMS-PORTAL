import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import LiveClass, LiveChatMessage, LiveClassAttendance

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.class_id = self.scope['url_route']['kwargs']['class_id']
        self.room_group_name = f'livechat_{self.class_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # Track Attendance Join
        if self.scope["user"].is_authenticated and not self.scope["user"].is_instructor:
            await self.track_join(self.class_id, self.scope["user"])

    async def disconnect(self, close_code):
        # Track Attendance Leave
        if self.scope["user"].is_authenticated and not self.scope["user"].is_instructor:
            await self.track_leave(self.class_id, self.scope["user"])

        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = self.scope["user"].username if self.scope["user"].is_authenticated else "Anonymous"
        full_name = self.scope["user"].get_full_name() or username

        # Save to database
        if self.scope["user"].is_authenticated:
            await self.save_message(self.class_id, self.scope["user"], message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'full_name': full_name,
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        full_name = event['full_name']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'full_name': full_name,
        }))

    @database_sync_to_async
    def save_message(self, class_id, user, message):
        live_class = LiveClass.objects.get(id=class_id)
        return LiveChatMessage.objects.create(live_class=live_class, user=user, message=message)

    @database_sync_to_async
    def track_join(self, class_id, user):
        live_class = LiveClass.objects.get(id=class_id)
        attendance, created = LiveClassAttendance.objects.get_or_create(
            student=user,
            live_class=live_class,
            defaults={'join_time': timezone.now()}
        )
        return attendance

    @database_sync_to_async
    def track_leave(self, class_id, user):
        try:
            attendance = LiveClassAttendance.objects.filter(
                student=user,
                live_class_id=class_id,
                leave_time__isnull=True
            ).latest('join_time')
            attendance.leave_time = timezone.now()
            # Calculate duration in minutes
            diff = attendance.leave_time - attendance.join_time
            attendance.duration = max(1, int(diff.total_seconds() / 60))
            attendance.save()
        except LiveClassAttendance.DoesNotExist:
            pass
