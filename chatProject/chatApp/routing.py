
from django.urls import re_path
from django.urls import path
from chatApp import consumers

websocket_urlpatterns = [
    # re_path(r'ws/chat/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
    path('ws/chat/<str:room_id>/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
    
]