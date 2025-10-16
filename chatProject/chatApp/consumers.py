import json
import re
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django_redis import get_redis_connection

def get_online_redis():
    """获取 chat-online 的 Redis 连接"""
    return get_redis_connection("chat-online")

class ChatConsumer(WebsocketConsumer):
    """聊天消费者"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_id = None
        self.user_id = None  # 当前用户ID

    def connect(self):
        # 获取当前用户
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            self.close()
            return
        self.user_id = user.id

        # 房间 ID
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_id = f'chat_{self.room_id}'
        self.accept()

        r = get_online_redis()
        # 记录在线连接（WebSocket）
        r.sadd(f"room:{self.room_id}:users", self.channel_name)
        # 记录浏览过的用户
        r.sadd(f"room:{self.room_id}:visited_users", self.user_id)

        # 加入组
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_id,
            self.channel_name,
        )

    def disconnect(self, close_code):
        r = get_online_redis()
        r.srem(f"room:{self.room_id}:users", self.channel_name)

        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_id,
            self.channel_name,
        )

    def receive(self, text_data=None, bytes_data=None):
        r = get_online_redis()
        muted_set = f"room:{self.room_id}:muted_users"

        # 禁言判断
        if r.sismember(muted_set, self.user_id):
            self.send(text_data=json.dumps({"error": "You are muted"}))
            return

        # 消息转发
        data = json.loads(text_data)
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
        """处理从 HTTP 接口发来的消息"""
        self.send(text_data=json.dumps(event))

    # ====== 辅助函数 ======
    @staticmethod
    def get_online_count(room_id: str) -> int:
        """获取房间当前在线人数"""
        r = get_online_redis()
        return r.scard(f"room:{room_id}:users")

    @staticmethod
    def get_visited_count(room_id: str) -> int:
        """获取房间浏览过的人数"""
        r = get_online_redis()
        return r.scard(f"room:{room_id}:visited_users")
