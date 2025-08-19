from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django_redis import get_redis_connection
from google.oauth2 import id_token

class IsAuthenticatedOrGuest(BasePermission):
    """
    允许已认证用户访问，如果没有认证（即没有 token），
    或者 token 已失效或者被黑名单标记，则返回游客身份信息。
    """

    def has_permission(self, request, view):
        # 检查是否有 Authorization 头部
        if 'Authorization' in request.headers:
            # 如果有 Authorization 头，尝试使用 token 进行认证
            auth = JWTAuthentication()
            try:
                # 尝试使用 token 进行认证
                user, _ = auth.authenticate(request)
                request.user = user  # 设置当前用户为认证用户

                # 获取 JWT 的 jti
                jti = _['jti']

                # 获取 Redis 连接
                redis_conn = get_redis_connection('session')

                # 检查 token 是否存在于黑名单中
                if redis_conn.get(jti):  # 如果 Redis 中存在该 jti，认为 token 已失效
                    raise AuthenticationFailed("Token is logout.")

                # 如果 token 在 Redis 中没有被标记为黑名单，认证通过
                return True

            except AuthenticationFailed:
                # 如果认证失败或者 token 被标记为黑名单，直接返回未认证状态
                return False
        else:
            # 如果没有 token，则认为是游客身份
            return True

