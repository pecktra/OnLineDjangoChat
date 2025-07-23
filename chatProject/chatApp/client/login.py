import re
import random
import string
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password
from rest_framework.response import Response
from rest_framework.decorators import api_view
from chatApp.models  import ChatUser
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from chatApp.permissions import IsAuthenticatedOrGuest
from rest_framework.decorators import api_view, permission_classes
from django_redis import get_redis_connection

@api_view(['POST'])
def register(request):
    """
    用户注册接口
    接受 username、password、email 参数，并对每个字段做详细限制：
      - username: 必须为3-30个字符，可以包含字母、数字、下划线和中文字符；
      - password: 至少8个字符，必须包含至少一个字母和一个数字；
      - email: 必须符合有效的邮箱格式。
    验证通过后创建用户，不生成 JWT 令牌，仅返回注册成功信息。
    """
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email')

    # 检查必填字段是否提供
    if not username or not password or not email:
        return Response({"code": 1, "message": "Username, password, and email are required."}, status=400)

    # 对 username 进行格式验证：3-30个字符，可包含字母、数字、下划线和中文字符
    username_regex = r'^[a-zA-Z0-9_\u4e00-\u9fa5]{3,30}$'
    if not re.match(username_regex, username):
        return Response({
            "code": 1,
            "message": "Username must be 3-30 characters long and can only contain letters, numbers, underscores, and Chinese characters."
        }, status=400)

    # 对 password 进行验证：至少8个字符，必须包含字母和数字
    if len(password) < 8:
        return Response({"code": 1, "message": "Password must be at least 8 characters long."}, status=400)
    if not re.search(r'[A-Za-z]', password, re.IGNORECASE) or not re.search(r'\d', password):
        return Response({"code": 1, "message": "Password must contain at least one letter and one number."}, status=400)

    # 对 email 进行格式验证
    try:
        validate_email(email)
    except ValidationError:
        return Response({"code": 1, "message": "Invalid email format."}, status=400)

    # 检查用户名是否已存在
    if ChatUser.objects.filter(username=username).exists():
        return Response({"code": 1, "message": "Username already exists."}, status=400)

    # 检查邮箱是否已注册
    if ChatUser.objects.filter(email=email).exists():
        return Response({"code": 1, "message": "Email is already registered."}, status=400)

    # 对密码进行加密处理
    password_hash = make_password(password)
    # 创建新用户记录
    user_account = ChatUser.objects.create(username=username, password=password_hash, email=email)

    # 返回注册成功信息，不生成 token
    return Response({
        'code': 0,
        'message': "Registration successful",
        'data': {
            'username': user_account.username,
            'email': user_account.email
        }
    })


# 登录时生成 JWT 响应的公共函数
def _generate_jwt_response(user_account, message):
    """
    生成 JWT 响应
    """
    refresh = RefreshToken.for_user(user_account)
    access_token = str(refresh.access_token)

    return Response({
        'code': 0,
        'message': message,
        'data': {
            'access_token': access_token,
            'refresh_token': str(refresh),
            'username': user_account.username,
            'email': user_account.email
        }
    })


@api_view(['POST'])
def user_login(request):
    """
    用户登录接口
    接受 username 和 password 参数，验证用户是否存在和密码是否正确，
    如果验证成功，则生成 JWT 令牌返回给客户端。
    """
    username = request.data.get('username')
    password = request.data.get('password')

    # 检查必填字段是否提供
    if not username or not password:
        return Response(
            {"code": 1, "message": "Username and password are required."},
            status=400
        )

    # 验证用户是否存在并验证密码
    user_account = authenticate(username=username, password=password)

    if not user_account:
        return Response(
            {"code": 1, "message": "Invalid credentials."},
            status=401
        )

    # 如果用户名和密码验证成功，返回 JWT
    jwt_response = _generate_jwt_response(user_account, "Login successful")

    return jwt_response

def generate_random_username():
    """生成一个随机的游客用户名"""
    length = random.randint(6, 12)  # 随机长度 6-12个字符
    random_username ='游客' + ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    return random_username

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 确保用户已认证或为游客
def is_logged_in(request):
    """
    检查用户是否已登录。
    如果用户已登录，返回用户信息及登录状态。
    如果未登录，返回随机生成的游客用户名。
    """
    user_account = request.user  # 获取当前认证的用户

    if user_account and user_account.is_authenticated:
        return Response({
            "code": 0,
            "message": "User is authenticated",
            "data": {
                "user_info": {
                    "uid": user_account.id,
                    "status": True,  # 用户已登录
                    "uname": user_account.username
                }
            }
        }, status=200)  # 登录成功时返回 200 OK

    # 未登录时返回随机生成的游客用户名
    random_username = generate_random_username()

    return Response({
        "code": 1,
        "message": "User is not authenticated",
        "data": {
            "user_info": {
                "uid": None,
                "status": False,  # 用户未登录
                "uname": random_username  # 返回生成的游客用户名
            }
        }
    })

#退出登录
@api_view(['POST'])
def logout(request):
    """
    用户退出登录接口
    1. 从 Authorization header 提取 token。
    2. 使用 `AccessToken` 解码 JWT。
    3. 获取 "exp"（过期时间）和 "jti"（JWT ID）。
    4. 将 "jti" 存储到 Redis 黑名单，并设置过期时间为 token 的生命周期。
    """
    # 从请求头中提取 token
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return Response({"code": 1, "message": "Missing Authorization header."}, status=400)

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return Response({"code": 1, "message": "Invalid Authorization header format."}, status=400)

    token = parts[1]

    # 使用 AccessToken 解码 token
    try:
        access_token = AccessToken(token)
        jti = access_token['jti']  # 获取唯一的 Token 标识符
        exp = access_token['exp']  # 获取过期时间戳
    except Exception as e:
        return Response({"code": 1, "message": f"Invalid or expired token. Error: {str(e)}"}, status=400)

    # 获取剩余有效期时间（单位：秒）
    import time
    current_timestamp = int(time.time())
    remaining_seconds = exp - current_timestamp
    if remaining_seconds <= 0:
        remaining_seconds = 0  # 确保没有负值

    # 将 jti 存入 Redis 黑名单
    try:
        redis_conn = get_redis_connection('session')  # 获取 Redis 连接
        redis_conn.setex(jti, remaining_seconds, "blacklisted")  # 设置过期时间
    except Exception as e:
        return Response({"code": 1, "message": f"Failed to connect to Redis. Error: {str(e)}"}, status=500)

    return Response({"code": 0, "message": "Logout successful."}, status=200)