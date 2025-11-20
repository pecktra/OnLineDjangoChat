
from django.urls import re_path
from django.urls import path
from chatApp import consumers

websocket_urlpatterns = [
    # re_path(r'ws/chat/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    path('ws/chat/<str:room_id>/', consumers.ChatConsumer.as_asgi()),#用户评论ws

    path('ws/aichat/<str:room_id>/', consumers.AIChatConsumer.as_asgi()),  # 主播ai聊天ws
    
]