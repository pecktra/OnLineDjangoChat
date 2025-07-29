import json
import re
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer

# from .models import Room


class ChatConsumer(WebsocketConsumer):
    '''聊天消费者'''
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_id = None
        self.room_name = None
        self.room_group_id = None


    def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_name = self.scope['url_route']['kwargs']['room_name']


        self.room_group_id = f'chat_{self.room_id}'
        self.accept()
        # 加入组
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_id,
            self.channel_name,
        )

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_id,
            self.channel_name,
        )


    def receive(self, text_data=None, bytes_data=None):

        # text_data_json = json.loads(text_data)
        # message = text_data_json['message']

        data = json.loads(text_data)
        # message = data.get("message")
        # room_id = data.get("username")

        # 发送消息事件到指定room
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_id,
            {
                'type': 'chat_user_message',
                'data': data,
            }
        )

    def chat_user_message(self, event):
        self.send(text_data=json.dumps(event))

    def chat_live_message(self, event):
        """处理从HTTP接口发来的消息"""
        self.send(text_data=json.dumps(event))
        
