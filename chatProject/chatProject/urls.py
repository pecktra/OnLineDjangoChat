"""
URL configuration for chatProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
# from chatApp.views import home,user_login,user_signup,user_logout
from chatApp.anchor import login , chat_data ,live
from chatApp.client import logins ,lives
from chatApp.balance import balance
# 导入静态文件模块，为了显示上传图片
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from . import settings
# from chatApp import views

from django.views.static import serve
from django.urls import re_path

from chatApp import views

urlpatterns = [

    path('admin/', admin.site.urls),
    # path('', home, name='home'), # 首页
    # path('login/', user_login, name='login'), # 登录
    # path('signup/', user_signup, name='signup'), # 注册
    # path('logout/', user_logout, name='logout'), # 退出
    # path('chat/<str:room_name>/', views.room_view, name='chatroom'), # 聊天室

    path('chat1/', views.room_test), # 聊天室


    #主播端
    path('api/users/register/',  login.register),  # 注册


    #主播端聊天数据
    path('api/chat/chat_data/', chat_data.chat_data),  # 聊天数据


    #主播端直播状态
    path('api/live/get_live_status/', live.get_live_status),
    path('api/live/change_live_status/', live.change_live_status),


    #客户端
    path('api/users/client_register/', logins.client_register),#注册
    path('api/users/user_login/', logins.user_login),#登录
    path('api/users/is_logged_in/', logins.is_logged_in),#检测是否登录
    path('api/users/logout/', logins.logout),#退出登录

    path('api/live/get_all_lives/', lives.get_all_lives),#获取正在直播的直播间列表
    path('api/live/get_live_info/', lives.get_live_info),#获取单个直播间信息
    path('api/live/get_live_chat_history/', lives.get_live_chat_history),#获取当前直播间主播历史消息数据
    path('api/live/get_user_chat_history/', lives.get_user_chat_history),#获取当前直播间用户历史消息数据   只获取最后20条数据
    path('', RedirectView.as_view(url='api/live/redirect_to_random_room/')),
    path('api/live/redirect_to_random_room/', lives.redirect_to_random_room),  # 获取当前直播间用户历史消息数据   只获取最后20条数据
    # path('/', lives.redirect_to_random_room),  # 获取当前直播间用户历史消息数据   只获取最后20条数据

    path('live/<str:room_name>/<str:room_id>/', lives.live_to_room, name='live_to_room'),
    path('api/live/save_user_chat_history/', lives.save_user_chat_history),  # 获取当前直播间用户历史消息数据   只获取最后20条数据

    #打赏
    path('api/balance/get_user_donations/', balance.get_user_donations),# 获取用户的所有打赏记录
    path('api/balance/get_anchor_donations/', balance.get_anchor_donations),# 获取主播收到的所有打赏记录
    path('api/balance/get_user_total_donated/', balance.get_user_total_donated),# 获取用户的总打赏金额
    path('api/balance/get_anchor_total_received/', balance.get_anchor_total_received)# 获取主播的总收到打赏金额
]




urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

