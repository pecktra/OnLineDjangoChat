import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django_redis import get_redis_connection
from django.conf import settings
from urllib.parse import parse_qs
import jwt
import threading

def get_online_redis():
    return get_redis_connection("chat-online")


class ChatConsumer(WebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group_id = None
        self.user_id = None
        self.User = None  # 延迟获取 Django 用户模型
        self.idle_timer = None


    def connect(self):
        # 延迟导入依赖 Django 的模块，避免顶层报错
        if self.User is None:
            from django.contrib.auth import get_user_model
            self.User = get_user_model()
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

        # 1️⃣ 从 query string 获取 JWT
        query_string = self.scope.get("query_string", b"").decode()
        query_params = parse_qs(query_string)
        token_list = query_params.get("token", [])
        token = token_list[0] if token_list else None
        if not token:
            self.close()
            return

        # 2️⃣ 验证 token
        try:
            UntypedToken(token)
        except (InvalidToken, TokenError):
            self.close()
            return

        # 3️⃣ 解码 token 获取用户
        try:
            decoded_data = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get("user_id")
            self.scope["user"] = self.User.objects.get(id=user_id)
        except (jwt.InvalidTokenError, self.User.DoesNotExist):
            self.close()
            return

        self.user_id = self.scope["user"].id

        # 4️⃣ 房间信息
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_id = f"chat_{self.room_id}"

        # 5️⃣ 接受 WebSocket
        self.accept()

        # 6️⃣ Redis 记录在线用户
        r = get_online_redis()
        r.sadd(f"room:{self.room_id}:users", self.channel_name)
        r.sadd(f"room:{self.room_id}:visited_users", self.user_id)

        # 7️⃣ 加入组
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_id, self.channel_name
        )


    def disconnect(self, close_code):
        r = get_online_redis()
        r.srem(f"room:{self.room_id}:users", self.channel_name)
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_id, self.channel_name
        )


    def receive(self, text_data=None, bytes_data=None):
        r = get_online_redis()
        muted_set = f"room:{self.room_id}:muted_users"
        if r.sismember(muted_set, self.user_id):
            self.send(text_data=json.dumps({"error": "You are muted"}))
            return

        data = json.loads(text_data)
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_id,
            {
                "type": "chat_user_message",
                "data": data,
            },
        )

    def chat_user_message(self, event):
        self.send(text_data=json.dumps(event))

    def chat_live_message(self, event):
        self.send(text_data=json.dumps(event))

    @staticmethod
    def get_online_count(room_id: str) -> int:
        r = get_online_redis()
        return r.scard(f"room:{room_id}:users")

    @staticmethod
    def get_visited_count(room_id: str) -> int:
        r = get_online_redis()
        return r.scard(f"room:{room_id}:visited_users")




class AIChatConsumer(WebsocketConsumer):
    def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_id = f"aichat_{self.room_id}"
        self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.room_group_id,
            self.channel_name
        )

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_id,
            self.channel_name
        )

    def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        message = data.get("message", "")
        # 简单回显
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_id,
            {
                "type": "chat_message",
                "message": f"AI 回复: {message}"
            }
        )

    def chat_message(self, event):
        self.send(text_data=json.dumps({
            "message": event["message"]
        }))