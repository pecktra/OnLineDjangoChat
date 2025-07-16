from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from chatApp.models import Anchor


#注册
@api_view(['POST'])
def register(request):
    """
    主播注册接口
    接收 username、handle、password 三个字段，要求字段必填，
    仅校验是否已存在，密码不做格式要求，注册成功后返回 uid。
    """
    username = request.data.get('username')
    handle = request.data.get('handle')
    password = request.data.get('password')

    # 必填校验
    if not username or not handle or not password:
        return Response({
            "code": 1,
            "message": "Username, handle, and password are required."
        }, status=400)

    # 唯一性校验
    if Anchor.objects.filter(username=username).exists():
        return Response({
            "code": 1,
            "message": "Username already exists."
        }, status=400)

    if Anchor.objects.filter(handle=handle).exists():
        return Response({
            "code": 1,
            "message": "Handle already exists."
        }, status=400)

    try:
        # 密码加密
        hashed_password = make_password(password)

        # 创建用户
        anchor = Anchor.objects.create(
            username=username,
            handle=handle,
            password=hashed_password
        )

        return Response({
            "code": 0,
            "message": "Registration successful.",
            "data": {
                "uid": str(anchor.uid),
                "username": anchor.username,
                "handle": anchor.handle
            }
        })

    except IntegrityError:
        return Response({
            "code": 1,
            "message": "Registration failed due to duplicate data."
        }, status=400)

    except Exception as e:
        return Response({
            "code": 1,
            "message": f"Unexpected error: {str(e)}"
        }, status=500)


