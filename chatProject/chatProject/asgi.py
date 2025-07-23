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
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from chatApp.routing import websocket_urlpatterns

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatProject.settings')

django_asgi_app = get_asgi_application() # 该行代码和下面一行代码顺序不能调换，否则会报错

from channels.auth import AuthMiddlewareStack  

application = ProtocolTypeRouter({
  'http': django_asgi_app,
  # 'websocket': URLRouter(
  #     chatApp.routing.websocket_urlpatterns
  #   ),
  'websocket': AuthMiddlewareStack(  # new
        URLRouter(
            websocket_urlpatterns
        )
    ),  # new
})
