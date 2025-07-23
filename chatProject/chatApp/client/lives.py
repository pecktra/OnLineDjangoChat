from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from chatApp.permissions import IsAuthenticatedOrGuest  # 自定义权限类
from django_redis import get_redis_connection  # 导入 Django-Redis 连接
from pymongo import MongoClient
from django.conf import settings
import json

# 获取 Redis 连接
redis_client = get_redis_connection('default')  # 使用 django-redis 配置

# 初始化 MongoDB 连接


client = MongoClient(settings.MONGO_URI)
db = client.chat_db  # 连接到 chat_db 数据库

# 初始化 Redis 连接
redis_conn = get_redis_connection('default')  # 默认的 Redis 配置，或者你可以根据配置指定其他连接池

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 需要游客或已认证用户访问
def get_all_lives(request):
    """
    获取正在直播的直播间列表
    GET /api/live/get_all_lives
    """
    try:
        live_status_list = []

        # 获取 MongoDB 中所有集合名
        collections = db.list_collection_names()

        # 遍历所有集合
        for collection_name in collections:
            collection = db[collection_name]
            user = collection.find_one({"uid": {"$exists": True}})  # 查找有用户信息的集合
            if user:
                # 获取相关信息
                uid = user.get("uid")
                username = user.get("username", "Unknown")
                character_name = user.get("character_name", "Unknown")

                # 构造 Redis 键，判断该房间是否正在直播
                live_key = f"live_status:{uid}:{character_name}"
                status_str = redis_conn.get(live_key)  # 获取 Redis 中的直播状态

                # 调试日志：查看 Redis 返回的状态
                print(f"Redis Key: {live_key}, Status: {status_str}")

                # 如果 Redis 中有值且是 "start"，则认为该房间正在直播
                if status_str and status_str.decode('utf-8') == "start":
                    live_num = user.get("live_num", 0)  # 获取当前直播间观看人数

                    live_status_list.append({
                        "room_id": collection_name,
                        "uid": uid,
                        "username": username,
                        "live_num": live_num,
                        "character_name": character_name
                    })

        return Response({
            "code": 0,
            "data": {
                "lives_info": live_status_list
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 需要游客或已认证用户访问
def get_live_info(request):
    """
    获取单个直播间信息
    GET /api/live/get_live_info
    """
    room_id = request.GET.get("room_id")

    if not room_id:
        return Response({"code": 1, "message": "Missing room_id parameter"}, status=400)

    try:
        # 从 room_id 中提取 uid 和 character_name
        uid, character_name = room_id.split('_')  # 假设 room_id 格式为 uid_character_name

        # 查询 Redis 获取直播状态
        live_key = f"live_status:{uid}:{character_name}"  # 使用 uid:character_name 作为 Redis 键

        # 使用 django-redis 获取 Redis 连接
        redis_conn = get_redis_connection('default')  # 使用默认的 Redis 配置
        status_str = redis_conn.get(live_key)  # 获取 Redis 中的直播状态

        if status_str:
            status_str = status_str.decode('utf-8').strip().lower()  # 解码为字符串并去掉空格/换行符
            print(f"Live status from Redis for {live_key}: {status_str}")  # 调试输出
        else:
            status_str = "stop"  # 如果 Redis 中没有找到，默认为停止状态

        # 判断直播状态
        live_status = True if status_str == "start" else False

        # 获取 MongoDB 中的直播信息
        collection = db.get_collection(room_id)  # 根据 room_id 获取对应的集合
        user = collection.find_one({"uid": uid})

        if user:
            live_num = user.get("live_num", 0)  # 直播间观看人数
            username = user.get("username", "Unknown")
            character_name = user.get("character_name", "Unknown")

            live_info = {
                "room_id": room_id,
                "uid": uid,
                "username": username,
                "live_num": live_num,
                "character_name": character_name,
                "live_status": live_status  # 开播状态，True/False
            }

            return Response({
                "code": 0,
                "data": {
                    "live_info": live_info
                }
            })

        return Response({"code": 1, "message": "Room not found in database."}, status=404)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 需要游客或已认证用户访问
def get_live_chat_history(request):
    """
    获取当前直播间主播历史消息数据
    GET /api/live/get_live_chat_history?room_id=<room_id>
    """
    room_id = request.GET.get("room_id")

    if not room_id:
        return Response({"code": 1, "message": "Missing room_id"}, status=400)

    try:
        # 获取 MongoDB 中该直播间的聊天数据集合
        collection = db[room_id]  # 假设每个直播间的聊天消息存储在以 room_id 命名的集合中

        # 查询该集合中的所有消息
        chat_history = collection.find()  # 获取所有消息

        # 格式化返回的数据
        chat_info = []
        for message in chat_history:
            # 直接获取 data 字段，它已经是字典形式
            data = message.get("data")

            # 获取消息内容
            live_message = data.get("mes")
            send_date = data.get("send_date")
            username = data.get("name")
            uid = data.get("uid")

            # 只取ai发送的消息
            if not data.get("is_user", False):
                chat_info.append({
                    "uid": uid,
                    "username": username,
                    "live_message": live_message,
                    "send_date": send_date
                })

        return Response({
            "code": 0,
            "data": {
                "chat_info": chat_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 需要游客或已认证用户访问
def get_user_chat_history(request):
    """
    获取当前直播间用户历史消息数据
    GET /api/live/get_user_chat_history?room_id=<room_id>
    """
    room_id = request.GET.get("room_id")

    if not room_id:
        return Response({"code": 1, "message": "Missing room_id"}, status=400)

    try:
        # 获取 MongoDB 中该直播间的聊天数据集合
        collection = db[room_id]  # 假设每个直播间的聊天消息存储在以 room_id 命名的集合中

        # 查询该集合中的所有消息，按照时间倒序排列，并限制返回最后 20 条消息
        chat_history = collection.find({"data.is_user": True})  # 只取用户的消息（is_user 为 True）
        chat_history = chat_history.sort("data.send_date", -1).limit(20)  # 排序并限制 20 条数据

        # 格式化返回的数据
        chat_info = []
        for message in chat_history:
            data = message.get("data")

            # 获取用户消息
            user_message = data.get("mes")
            send_date = data.get("send_date")
            username = data.get("name")
            uid = data.get("uid")

            chat_info.append({
                "uid": uid,
                "username": username,
                "send_date": send_date,
                "user_message": user_message
            })

        return Response({
            "code": 0,
            "data": {
                "chat_info": chat_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])  # 需要游客或已认证用户访问
def redirect_to_random_room(request):
    """
    随机选择一个正在直播的房间，并重定向到该房间的页面
    GET /api/live/redirect_to_random_room
    """
    try:
        # 从 Redis 中获取所有正在直播的房间状态
        keys = redis_client.keys('live_status:*')  # 获取所有直播状态的键（以 live_status: 开头）

        live_rooms = []

        # 遍历所有的 live_status 键
        for key in keys:
            status = redis_client.get(key)  # 获取每个房间的直播状态
            if status == b'start':  # 只选择状态为 'start' 的房间
                room_id = key.decode('utf-8').replace('live_status:', '')  # 去掉 'live_status:' 前缀，得到房间 ID
                live_rooms.append(room_id)

        # 如果没有找到正在直播的房间，返回错误信息
        if not live_rooms:
            return Response({"code": 1, "message": "No live rooms found."}, status=400)

        # 随机选择一个正在直播的房间
        random_room_id = random.choice(live_rooms)

        # 构造重定向的 URL，假设页面是 'room.html?room_id=<room_id>'
        redirect_url = f"/room.html?room_id={random_room_id}"

        # 重定向到该 URL
        return redirect(redirect_url)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)