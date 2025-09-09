from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_redis import get_redis_connection  # 使用 django-redis 连接 Redis
from django.conf import settings
from pymongo import MongoClient
from chatApp.models import RoomInfo, Anchor
from django.http import JsonResponse
import json
from django.utils import timezone

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.chat_db  # 连接到 chat_db 数据库

# 获取 Redis 连接
redis_client = get_redis_connection('default')  # 使用 django-redis 配置
redis_chat_limit_client = get_redis_connection('chat-limit')  # 使用 django-redis 配置
@api_view(['GET'])
def get_live_status(request):
    """
    获取当前主播直播间状态列表
    GET /api/live/get_live_status?uid=<uid>&username=<username>
    """
    uid = request.GET.get("uid")
    username = request.GET.get("username")

    if not uid or not username:
        return Response({"code": 1, "message": "Missing uid or username"}, status=400)
    
    # 从roomInfo里面获取房间信息
    room_infos = RoomInfo.objects.filter(uid=uid)
    live_status_list = []
    if room_infos:
        for room_info in room_infos:

            status = True
            status_str = redis_client.get(room_info.room_id)
            if status_str is None:
                status = False  # 没有就说明没有直播

            room = {
                    "title":room_info.title,
                    "coin_num":room_info.coin_num,
                    "room_type":room_info.room_type
                }  # 返回房间信息
            if room_info.is_info == 0:
                room = None
            

            live_status_list.append({
                "uid": uid,
                "user_name":room_info.user_name,
                "room_id":room_info.room_id,
                "room_name":room_info.room_name,
                "character_name": room_info.character_name,
                "character_date":room_info.character_date,
                "status": status,
                "room_info": room
            })

    # 返回查询结果
    return Response({
        "code": 0,
        "data": {
            "live_status": live_status_list
        }
    })


@api_view(['POST'])
def change_live_status(request):
    """
    修改直播间直播状态
    POST /api/live/change_live_status
    """
    uid = request.data.get("uid")
    room_id = request.data.get("room_id")
    character_name = request.data.get("character_name")
    character_date = request.data.get("character_date")
    live_status = request.data.get("live_status")

    if not uid or not character_name or not live_status:
        return Response({"code": 1, "message": "Missing parameter(s)."}, status=400)

    if live_status not in ["start", "stop"]:
        return Response({"code": 1, "message": "Invalid live_status, must be 'start' or 'stop'."}, status=400)

    try:


        # 使用 Redis 原子操作设置直播状态
        redis_client.set(room_id, live_status)

        return Response({"code": 0, "message": "Live status updated successfully."})

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['POST'])
def add_room_info(request):
    """
    创建一个房间
    POST /api/live/add_room_info
    """
    try:
        # 获取请求中的参数
        uid = request.data.get('uid')
        user_name = request.data.get('user_name')
        room_id = request.data.get("room_id")
        room_name = request.data.get("room_name")
        character_name = request.data.get('character_name')
        character_date = request.data.get('character_date')
        title = request.data.get('title')
        describe = request.data.get('describe')
        coin_num = request.data.get('coin_num')
        room_type = request.data.get('room_type')

        # 参数验证
        if not uid or not character_name or not character_date or not title or coin_num is None or room_type is None:
            return Response({"code": 1, "message": "Missing required parameters"}, status=400)

        try:
            room_type = int(room_type)
        except ValueError:
            return Response({"code": 1, "message": "Invalid room_type, must be an integer."}, status=400)

        # 验证房间类型是否合法
        if room_type not in [0, 1, 2]:
            return Response({"code": 1, "message": "Invalid room_type, must be 0 (Free), 1 (VIP), or 2 (1v1)."}, status=400)

        # 检查是否已经存在相同的房间（根据 uid 和 character_name 查找）

        room_info = RoomInfo.objects.filter(room_id = room_id).first()
        coin_num_info = room_info.coin_num
        if coin_num_info:
            return Response({"code": 1, "message": "Room with the given uid and character_name already exists."}, status=400)

        # 使用 update_or_create 实现更新或创建
        room_info, created = RoomInfo.objects.update_or_create(
            room_id=room_id,  # 查找条件
            defaults={
                'uid': uid,
                'user_name': user_name,
                'room_name': room_name,
                'character_name': character_name,
                'character_date': character_date,
                'title': title,
                'describe':describe,
                'coin_num': coin_num,
                'room_type': room_type,
                'is_info':1
            }
        )



        # 返回成功响应
        return Response({"code": 0, "message": "Room created successfully"}, status=201)

    except Anchor.DoesNotExist:
        # 如果没有找到对应的 anchor 对象
        return Response({"code": 1, "message": "Anchor with the given uid does not exist."}, status=400)
    except Exception as e:
        # 处理其他异常
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)






@api_view(['POST'])
def check_api_limit(request):
    """
    创建一个房间
    POST /api/live/check_api_limit
    """
    
    # 获取请求中的参数
    uid = request.data.get('uid')
    chat_limit = 50
    # 参数验证
    if not uid :
        return Response({"code": 1, "message": "Missing required parameters"}, status=400)
    
    
    # 获取今天的日期
    today = timezone.now().date().strftime('%Y-%m-%d')
    redis_key = uid+":"+today
    value = redis_chat_limit_client.get(redis_key)
    if value is None:
        redis_chat_limit_client.set(redis_key, 1, ex=2*24*60*60)  # 没有就说明今天没有聊天
        return Response({"code": 0, "message": "true"}, status=200)
    value = int(value)
    if int(value) < chat_limit:
        redis_chat_limit_client.set(redis_key, value+1, ex=2*24*60*60)
        return Response({"code": 0, "message": "true"}, status=200)
    
    
    # 返回失败响应
    return Response({"code": 1, "message": f"{chat_limit} API calls per day have exceeded the limit."}, status=200)










