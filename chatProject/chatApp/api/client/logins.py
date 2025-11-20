
import random
import string
import requests
import urllib.parse
import uuid
from django.contrib.auth import login, get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password
import os
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from chatApp.models  import ChatUser,UserBalance
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import api_view, permission_classes
from django_redis import get_redis_connection
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport.requests import Request
from django.shortcuts import redirect
from django.contrib.auth import get_user
from rest_framework.response import Response
from django.contrib.auth import logout
from chatApp.api.common.payment import process_referral_reward
from rest_framework.permissions import IsAuthenticated
from urllib.parse import urlparse, parse_qs, unquote, urlencode

def generate_random_username():
    """生成一个随机的游客用户名"""
    length = random.randint(6, 12)  # 随机长度 6-12个字符
    random_username ='游客' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return random_username

@api_view(['GET'])
def google_oauth2_url(request):
    """
    获取 Google OAuth2 授权 URL（前端跳转用）
    支持携带 ref 参数（例如推荐码、来源等）
    """
    ref = request.GET.get("ref")  # 可选参数
    state = str(uuid.uuid4())  # 生成随机 state 防止 CSRF 攻击


    # 基础授权参数
    params = {
        "client_id": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        "redirect_uri": settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,  # 这里传 state 防止伪造请求
        "access_type": "offline",
        "prompt": "consent"
    }

    # 如果前端传了 ref，就追加到 state 或 redirect_uri 上
    if ref:
        params["state"] = f"{state}|ref={ref}"

    authorization_url = f"https://accounts.google.com/o/oauth2/auth?{urllib.parse.urlencode(params)}"

    return Response({
        "code": 0,
        "message": "Authorization domain extracted successfully",
        "data": {
            "authorization_url": authorization_url
        }
    })

# 
# @api_view(['GET'])
# def google_oauth2_callback(request):
#     """
#     Google 回调：使用授权码换取 access_token，并获取用户信息。
#     支持从 state 中恢复 ref 参数。
#     """
#     code = request.GET.get('code')
#     state = request.GET.get('state')
#
#     if not code:
#         return Response({
#             "code": 1,
#             "message": "Authorization code not provided",
#             "data": {}
#         }, status=400)
#
#     # 提取 ref 参数（从 state 中安全获取）
#     referrer_id = None
#     if state and "|ref=" in state:
#         try:
#             referrer_id = int(state.split("|ref=")[1])
#         except ValueError:
#             referrer_id = None
#
#     # 交换 token
#     url = 'https://oauth2.googleapis.com/token'
#     data = {
#         'code': code,
#         'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
#         'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
#         'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
#         'grant_type': 'authorization_code',
#     }
#
#     response = requests.post(url, data=data)
#     tokens = response.json()
#
#     if 'access_token' not in tokens:
#         return Response({
#             "code": 2,
#             "message": "Failed to retrieve access token from Google",
#             "data": tokens
#         }, status=400)
#
#     # 请求 Google 用户信息
#     user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
#     headers = {'Authorization': f"Bearer {tokens['access_token']}"}
#     user_info_response = requests.get(user_info_url, headers=headers)
#     user_info = user_info_response.json()
#
#
#     if 'email' not in user_info or 'id' not in user_info:
#         return Response({
#             "code": 3,
#             "message": "Failed to retrieve Google user information",
#             "data": {}
#         }, status=400)
#
#     google_email = user_info['email']
#     google_name = user_info.get('name')
#     google_avatar = user_info.get('picture')
#     google_id = user_info.get('id')
#
#     # 查找或创建用户
#     user, created = ChatUser.objects.get_or_create(
#         google_id=google_id,
#         defaults={
#             'email': google_email,
#             'avatar': google_avatar,
#             'username': google_name,
#             'referrer_id': referrer_id
#         }
#     )
#
#     # 如果存在则更新
#     user_updated = False
#     if user.email != google_email:
#         user.email = google_email
#         user_updated = True
#     if user.username != google_name:
#         user.username = google_name
#         user_updated = True
#     if user.avatar != google_avatar:
#         user.avatar = google_avatar
#         user_updated = True
#     if user_updated:
#         user.save()
#
#
#     # 登录并保存会话
#     login(request, user)
#     request.session['google_name'] = google_name
#     request.session['google_email'] = google_email
#     request.session['google_id'] = google_id
#     request.session['user_id'] = user.id
#     request.session.save()
#
#     # ✅ 仅在用户首次绑定时设置邀请人
#     if not user.referrer_id and referrer_id:
#         user.referrer_id = referrer_id
#         user_updated = True
#         # 首次绑定才发放邀请奖励
#         process_referral_reward(user.id, referrer_id)
#
#     if user_updated:
#         user.save()
#
#     #成功后重定向（例如跳转前端首页或来源页）
#
#     site_domain = os.environ.get('SITE_DOMAIN')
#     return redirect(site_domain)


@api_view(['GET'])
def google_logout(request):
    """
    退出 Google 登录
    如果用户已登录，则清除会话并退出；
    如果未登录，则提示“Please login first”。
    """

    # 判断是否有登录信息
    if not request.session.get("user_id"):
        return Response({
            "code": 1,
            "message": "Please login first"
        })

    # 调用 Django 的 logout 方法来退出当前用户
    logout(request._request)

    # 清除与 Google 登录相关的会话信息
    request.session['google_name'] = None
    request.session['google_email'] = None
    request.session['google_id'] = None
    request.session['user_id'] = None
    request.session.save()  # 显式保存会话

    # 已登录 → 退出成功后重定向
    return redirect('/')


@api_view(['GET'])
def google_login_callback(request):
    """
    Google OAuth2 回调：使用授权码换取 access_token，并获取用户信息。
    返回 JWT + Google 用户信息。
    """
    code = request.GET.get('code')
    state = request.GET.get('state')

    if not code:
        return Response({
            "code": 1,
            "message": "Authorization code not provided",
            "data": {}
        }, status=400)

    # 提取 ref 参数
    referrer_id = None
    if state and "|ref=" in state:
        try:
            referrer_id = int(state.split("|ref=")[1])
        except ValueError:
            referrer_id = None

    # 1️⃣ 向 Google 换取 Access Token
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }
    token_response = requests.post(token_url, data=token_data)
    tokens = token_response.json()

    if 'access_token' not in tokens:
        return Response({
            "code": 2,
            "message": "Failed to retrieve access token from Google",
            "data": tokens
        }, status=400)

    # 2️⃣ 获取 Google 用户信息
    user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}
    user_info = requests.get(user_info_url, headers=headers).json()

    if 'email' not in user_info or 'id' not in user_info:
        return Response({
            "code": 3,
            "message": "Failed to retrieve Google user information",
            "data": {}
        }, status=400)

    google_email = user_info['email']
    google_name = user_info.get('name')
    google_avatar = user_info.get('picture')
    google_id = user_info.get('id')

    # 3️⃣ 查找或创建 ChatUser
    user, created = ChatUser.objects.get_or_create(
          google_id=google_id,
           defaults={
             'email': google_email,
             'avatar': google_avatar,
             'username': google_name,
             'referrer_id': referrer_id
          }
      )

    user_updated = False
    if user.email != google_email:
        user.email = google_email
        user_updated = True
    if user.username != google_name:
        user.username = google_name
        user_updated = True
    if user.avatar != google_avatar:
        user.avatar = google_avatar
        user_updated = True

        # ✅ 首次绑定邀请人
    if not user.referrer_id and referrer_id:
        user.referrer_id = referrer_id
        user_updated = True
        process_referral_reward(user.id, referrer_id)

    if user_updated:
        user.save()

    # 4️⃣ 生成 JWT Token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # 5️⃣ 返回前端
    return Response({
        "code": 0,
        "message": "Google 登录成功",
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user_info": {
                "id": user.id,
                "google_id": google_id,
                "email": google_email,
                "username": google_name,
                "avatar": google_avatar,
                "nickname": getattr(user, "nickname", ""),
                "referrer_id": user.referrer_id,
            }
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_nickname(request):
    """
    修改用户昵称（需要登录）
    POST /api/user/update_nickname/
    参数:
    - nickname: 新昵称
    """
    user = request.user
    nickname = request.data.get('nickname', '').strip()

    if not nickname:
        return Response({"code": 1, "message": "昵称不能为空"}, status=400)

    # 检查昵称是否重复
    if ChatUser.objects.filter(nickname=nickname).exclude(id=user.id).exists():
        return Response({"code": 2, "message": "该昵称已被使用"}, status=400)

    # 更新昵称
    user.nickname = nickname
    user.save()

    return Response({
        "code": 0,
        "message": "昵称修改成功",
        "data": {
            "id": user.id,
            "nickname": user.nickname,
            "avatar": user.avatar
        }
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_info(request):
    user = request.user
    user_info = {
        "id": user.id,
        "google_id": getattr(user, "google_id", ""),
        "email": getattr(user, "email", ""),
        "username": getattr(user, "username", ""),
        "avatar": getattr(user, "avatar", ""),
        "nickname": getattr(user, "nickname", ""),
        "referrer_id": getattr(user, "referrer_id", None),
    }
    return Response({
        "code": 0,
        "message": "获取用户信息成功",
        "data": {
            "user_info": user_info
        }
    })