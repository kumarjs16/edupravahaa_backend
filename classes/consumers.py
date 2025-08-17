import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ClassSchedule, ClassAttendance
from courses.models import Enrollment

class WebRTCSignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'webrtc_{self.room_id}'
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user has access to this room
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that user joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user_id': str(self.user.id),
                'username': self.user.get_full_name() or self.user.username,
                'role': self.user.role
            }
        )
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        
        # Notify others that user left
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_left',
                'user_id': str(self.user.id)
            }
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'offer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_offer',
                    'offer': data['offer'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        elif message_type == 'answer':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_answer',
                    'answer': data['answer'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        elif message_type == 'ice-candidate':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_ice_candidate',
                    'candidate': data['candidate'],
                    'sender_id': str(self.user.id),
                    'target_id': data.get('target_id')
                }
            )
        
        elif message_type == 'end-session' and self.user.is_teacher:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'session_ended'
                }
            )
    
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-joined',
            'user_id': event['user_id'],
            'username': event['username'],
            'role': event['role']
        }))
    
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'user-left',
            'user_id': event['user_id']
        }))
    
    async def webrtc_offer(self, event):
        # Send offer only to target user or all if no target specified
        if not event.get('target_id') or event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'offer': event['offer'],
                'sender_id': event['sender_id']
            }))
    
    async def webrtc_answer(self, event):
        # Send answer only to target user
        if event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'answer': event['answer'],
                'sender_id': event['sender_id']
            }))
    
    async def webrtc_ice_candidate(self, event):
        # Send ICE candidate only to target user or all if no target
        if not event.get('target_id') or event['target_id'] == str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'candidate': event['candidate'],
                'sender_id': event['sender_id']
            }))
    
    async def session_ended(self, event):
        await self.send(text_data=json.dumps({
            'type': 'session-ended'
        }))
    
    @database_sync_to_async
    def check_room_access(self):
        # Teachers can access their own class rooms
        if self.user.is_teacher:
            return ClassSchedule.objects.filter(
                meeting_room_id=self.room_id,
                teacher=self.user
            ).exists()
        
        # Students can access if enrolled in the course
        if self.user.is_student:
            class_schedule = ClassSchedule.objects.filter(
                meeting_room_id=self.room_id
            ).first()
            
            if class_schedule:
                return Enrollment.objects.filter(
                    student=self.user,
                    course=class_schedule.course,
                    payment_status='completed'
                ).exists()
        
        # Admins can access any room
        return self.user.is_admin