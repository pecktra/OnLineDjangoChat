import re
import random
import string
import requests
from django.contrib.auth import login, get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password
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

def generate_random_username():
    """生成一个随机的游客用户名"""
    length = random.randint(6, 12)  # 随机长度 6-12个字符
    random_username ='游客' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return random_username

@api_view(['GET'])
def google_oauth2_url(request):
    """
    返回 Google OAuth2 授权 URL，前端可通过此 URL 跳转到 Google 登录页面。
    """
    authorization_url = f"https://accounts.google.com/o/oauth2/auth?client_id={settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY}&redirect_uri={settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI}&response_type=code&scope=openid%20email%20profile"
    return Response({
        "code": 0,
        "message": "Authorization URL generated successfully",
        "data": {
            "authorization_url": authorization_url
        }
    })


@api_view(['GET'])
def google_oauth2_callback(request):
    """
    使用授权码获取 Google 访问令牌，并获取用户信息（Google ID、邮箱、头像等）。
    如果用户不存在则创建用户，已存在则更新用户信息。
    """
    code = request.GET.get('code')

    if not code:
        return Response({
            "code": 1,
            "message": "Authorization code not provided",
            "data": {}
        }, status=400)

    # 使用授权码获取访问令牌
    url = 'https://oauth2.googleapis.com/token'
    data = {
        'code': code,
        'client_id': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
        'client_secret': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
        'redirect_uri': settings.SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI,
        'grant_type': 'authorization_code',
    }

    response = requests.post(url, data=data)
    tokens = response.json()

    if 'access_token' in tokens:
        # 使用访问令牌获取用户信息
        user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        user_info_response = requests.get(user_info_url, headers=headers)
        user_info = user_info_response.json()

        if 'email' not in user_info or 'id' not in user_info:
            return Response({
                "code": 1,
                "message": "Failed to retrieve Google user information",
                "data": {}
            }, status=400)

        google_email = user_info['email']
        google_name = user_info.get('name')
        google_avatar = user_info.get('picture')
        google_id = user_info.get('id')

        # 查找或创建用户
        user, created = ChatUser.objects.get_or_create(
            google_id=google_id,  # 根据 Google ID 查找或创建
            defaults={
                'email': google_email,
                'avatar': google_avatar,
                'username': google_name  # 将 google_name 存入 username
            }
        )

        # 如果用户已存在，检查是否有变化并更新信息
        if not created:
            # 如果信息发生变化，则更新用户
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

            # 如果有任何变化，保存用户信息
            if user_updated:
                user.save()

        # 登录用户
        login(request, user)
        request.session['google_name'] = google_name
        request.session['google_email'] = google_email
        request.session['google_id'] = google_id
        request.session['user_id'] = user.id
        request.session.save()  # 显式保存会话


        redirect_url = request.META.get('HTTP_REFERER','/')


        # 重定向到上一个页面
        return redirect(redirect_url)

    return Response({
        "code": 1,
        "message": "Failed to retrieve access token from Google",
        "data": {}
    }, status=400)


@api_view(['GET'])
def is_google_logged_in(request):
    """
    检查用户是否通过 Google 登录。
    如果用户已通过 Google 登录，返回用户信息，包括余额（coin_num）。
    如果未通过 Google 登录，返回游客模式。
    """
    user = get_user(request)  # 获取当前用户

    if user and user.is_authenticated:
        # 用户已登录，检查是否通过 Google 登录
        google_id = request.session.get('google_id')
        google_name = request.session.get('google_name')
        google_email = request.session.get('google_email')

        if google_id and google_name:
            # 如果有 google_id 和 google_email，表示用户是通过 Google 登录的
            try:
                # 获取用户余额
                user_balance = UserBalance.objects.get(user_id=user.id)
                coin_num = user_balance.balance  # 假设 balance 字段存储了用户的钻石余额
            except UserBalance.DoesNotExist:
                coin_num = 0  # 如果用户没有余额记录，默认余额为 0

            return Response({
                "code": 0,
                "message": "User is authenticated via Google",
                "data": {
                    "user_info": {
                        "uid": user.id,
                        "status": True,  # 用户已登录
                        "uname": google_name,  # 使用 Google 的 email 作为用户名
                        "google_id": google_id,
                        "google_email": google_email,
                        "coin_num": coin_num  # 返回用户余额
                    }
                }
            }, status=200)  # 登录成功时返回 200 OK

    # 如果没有通过 Google 登录信息，返回游客模式
    random_username = generate_random_username()

    return Response({
        "code": 1,
        "message": "User is not authenticated via Google, using guest mode",
        "data": {
            "user_info": {
                "uid": None,
                "status": False,  # 用户未登录
                "uname": random_username,  # 返回生成的游客用户名
                "google_id": None,
                "google_email": None,
                "coin_num": 0  # 游客的余额默认为 0
            }
        }
    }, status=200)  # 仍然返回 200 OK，但表示未通过 Google 登录，使用游客模式

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

