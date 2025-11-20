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
from chatApp.api.anchor import login, chat_data, live, card
from chatApp.api.client import logins, lives, subscription, follow, chat ,feedhome,favorite
from chatApp.api.balance import balance
from chatApp.api.payment import payment
from chatApp.api.fork import fork
from chatApp.api.fork import fork_chat
from chatApp.api.preset import preset_save
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
    path('chat1/', views.room_test), # 聊天室

    #主播端
    path('api/users/register/',  login.register),  # 注册

    #主播端聊天数据
    path('api/chat/chat_data/', chat_data.chat_data),  # 聊天数据
    path('api/card/import_card/', card.import_card),  # 导入卡片信息

    #主播端直播状态
    path('api/live/add_room_info/', live.add_room_info),
    path('api/live/check_api_limit/', live.check_api_limit),



    # Google 登录相关 URL
    path('api/users/google_login_url/', logins.google_oauth2_url),  # 获取 Google 登录授权 URL
    # path('api/users/google_oauth2_callback/', logins.google_oauth2_callback),  # Google 登录回调处理
    path('api/users/google_login_callback/', logins.google_login_callback),  # Google 新前端登录回调处理
    path('api/users/update_nickname/', logins.update_nickname),  # 修改昵称
    path('api/users/google_logout/', logins.google_logout),#退出登录
    path('api/users/get_user_info/', logins.get_user_info),#获取用户信息

    #直播首页
    path('api/live/get_all_lives/', lives.get_all_lives),#获取直播间列表
    path('api/live/get_live_info/', lives.get_live_info),#获取单个直播间信息
    path('api/live/get_user_chat_history/', lives.get_user_chat_history),#获取当前直播间用户历史消息数据
    path('', lives.home_view, name='home'),  # Root path renders room_v3.html
    path('live/<str:room_id>/', lives.live_to_room, name='live_to_room'),
    path('api/live/save_user_chat_history/', lives.save_user_chat_history),  # 保存用户评论
    path('api/live/pay_vip_coin/', lives.pay_vip_coin), #用户支付 VIP 钻石订阅vip直播间


    #打赏
    path('api/balance/get_user_donations/', balance.get_user_donations),# 获取用户的所有打赏记录
    path('api/balance/get_anchor_donations/', balance.get_anchor_donations),# 获取主播收到的所有打赏记录
    path('api/balance/get_user_total_donated/', balance.get_user_total_donated),# 获取用户的总打赏金额
    path('api/balance/get_anchor_total_received/', balance.get_anchor_total_received),# 获取主播的总收到打赏金额
    path('api/balance/make_donation/', balance.make_donation),# 用户打赏主播接口

    #订阅
    path('api/subscription/subscribe_to_anchor/', subscription.subscribe_to_anchor),# 用户订阅主播
    path('api/subscription/get_subscriptions/', subscription.get_subscriptions),# 用户订阅列表

    #关注
    path('api/follow/toggle_follow_user/', follow.toggle_follow_user), # 关注
    path('api/follow/get_followed_users/', follow.get_followed_users),  # 用户关注列表

    #支付
    path('api/payment/process_recharge/', payment.process_recharge),  # 充值
    path('api/payment/payment_callback/', payment.payment_callback),  # 回调
    path('api/payment/check_payment_status/<str:order_id>/', payment.check_payment_status),  # 查询订单状态

    #聊天列表
    path('api/chat/get_room_chat/', chat.get_room_chat),  # 聊天列表

    #fork
    path('api/fork/fork_confirm/', fork.fork_confirm),#确认fork
    path('api/fork/forked_list/', fork.forked_list),#我fork的
    path('api/fork/anchor_forked_by/', fork.anchor_forked_by),#被fork过
    path('api/fork/fork_chat/', fork_chat.fork_chat),#fork后续聊天

    #feed
    path('api/feed/get_latest_ai_rooms/', feedhome.get_latest_ai_rooms),#信息流页面
    path('api/feed/get_fork_relations/', feedhome.get_fork_relations),#fork信息
    path('api/feed/random_fork_card/', feedhome.random_fork_card),#随机foek信息

    #favorite
    path('api/favorite/favorite_card/', favorite.favorite_card),#收藏、取消收藏
    path('api/favorite/favorite_list/', favorite.favorite_list),#收藏列表


    #preset
    path('api/preset/preset_save/', preset_save.preset_save),#保存预设
    


]




urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)

