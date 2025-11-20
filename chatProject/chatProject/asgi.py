"""
ASGI config for chatProject project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatProject.settings')

# application = get_asgi_application()
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatProject.settings')  # ⚠️ 必须最先设置

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from chatApp.routing import websocket_urlpatterns

# Django HTTP ASGI 应用
django_asgi_app = get_asgi_application()

# Channels 路由
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
