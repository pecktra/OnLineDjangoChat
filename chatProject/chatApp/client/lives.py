from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from chatApp.permissions import IsAuthenticatedOrGuest
from django_redis import get_redis_connection
from pymongo import MongoClient
from django.conf import settings
import json
import random
from django.shortcuts import redirect, render
from chatApp.models import ChatUserChatHistory
from django.utils import timezone
import hashlib

# 获取 Redis 连接
redis_client = get_redis_connection('default')

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# 直播间相关 API
@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])
def get_all_lives(request):
    """
    获取正在直播的直播间列表
    GET /api/live/get_all_lives
    """
    try:
        live_status_list = []
        collections = db.list_collection_names()

        for collection_name in collections:
            collection = db[collection_name]
            user = collection.find_one({"uid": {"$exists": True}})
            if user:
                uid = user.get("uid")
                username = user.get("username", "Unknown")
                character_name = user.get("character_name", "Unknown")
                live_key = f"live_status:{uid}:{character_name}"
                status_str = redis_client.get(live_key)
                print(f"Redis Key: {live_key}, Status: {status_str}")

                if status_str and status_str.decode('utf-8') == "start":
                    room_id = hashlib.md5(collection_name.encode('utf-8')).hexdigest()
                    live_num = user.get("live_num", 0)

                    live_status_list.append({
                        "room_name": collection_name,
                        "room_id": room_id,
                        "uid": uid,
                        "username": username,
                        "live_num": live_num,
                        "character_name": character_name
                    })

        return Response({
            "code": 0,
            "data": {"lives_info": live_status_list}
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])
def get_live_info(request):
    """
    获取单个直播间信息
    GET /api/live/get_live_info?room_name=<room_name>
    """
    room_name = request.GET.get("room_name")
    if not room_name:
        return Response({"code": 1, "message": "Missing room_name parameter"}, status=400)

    try:
        collection = db[room_name]  # 使用 room_name 直接访问集合
        room_data = collection.find_one({"room_name": room_name})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        room_id = room_data.get("room_id")
        # 从 room_name 提取 uid 和 character_name
        uid = room_name.split('_')[0]
        character_name = room_name.split('_')[1]

        # 获取 live_status
        live_key = f"live_status:{uid}:{character_name}"
        status_str = redis_client.get(live_key)
        live_status = status_str.decode('utf-8').strip().lower() == "start" if status_str else False

        # 获取用户信息，直接从 room_data 中获取
        username = room_data.get("username", "Unknown")
        live_num = room_data.get("live_num", 0)  # 假设 "live_num" 存在于 room_data 中

        # 构建返回的 live_info
        live_info = {
            "room_name": room_name,
            "room_id": room_id,
            "uid": uid,
            "username": username,
            "live_num": live_num,
            "character_name": character_name,
            "live_status": live_status
        }

        return Response({"code": 0, "data": {"live_info": live_info}})

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])
def get_live_chat_history(request):
    """
    获取当前直播间主播历史消息数据
    GET /api/live/get_live_chat_history?room_name=<room_name>
    """
    room_name = request.GET.get("room_name")
    if not room_name:
        return Response({"code": 1, "message": "Missing room_name"}, status=400)

    try:
        # 使用 room_name 访问集合
        collection = db[room_name]
        room_data = collection.find_one({"room_name": room_name})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        room_id = room_data.get("room_id")
        if not room_id:
            return Response({"code": 1, "message": "room_id not found for the provided room_name."}, status=404)

        # 提取 uid 和 character_name
        uid = room_name[:room_name.rfind('_')]
        character_name = room_name[room_name.rfind('_') + 1:]

        # 使用 room_id 访问聊天数据集合
        collection = db.get_collection(room_name)
        chat_history = collection.find()

        # 获取主播的 username（从 room_data 中提取）
        username = room_data.get("username", "Unknown")

        # 格式化聊天历史
        chat_info = []
        for message in chat_history:
            data = message.get("data", {})
            live_message = data.get("mes")
            send_date = data.get("send_date")
            message_username = data.get("name", "Unknown")
            is_user = data.get("is_user", False)

            sender_name = message_username if is_user else message.get("character_name", "ai")
            print(sender_name)
            chat_info.append({
                "is_user": is_user,
                "live_message": live_message,
                "sender_name": sender_name,
                "send_date": send_date
            })

        print(chat_info)
        return Response({
            "code": 0,
            "data": {
                "room_name": room_name,
                "room_id": room_id,
                "uid": uid,
                "username": username,  # 使用主播的 username
                "chat_info": chat_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])
def get_user_chat_history(request):
    """
    获取当前直播间用户历史消息数据
    GET /api/live/get_user_chat_history?room_name=<room_name>
    """
    room_name = request.GET.get("room_name")
    if not room_name:
        return Response({"code": 1, "message": "Missing room_name"}, status=400)

    try:
        # 获取房间数据
        collection = db[room_name]
        room_data = collection.find_one({"room_name": room_name})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        # 直接使用 room_name 作为 room_id
        room_id = room_name
        if not room_id:
            return Response({"code": 1, "message": "room_id not found for the provided room_name."}, status=404)

        uid = room_name[:room_name.rfind('_')]
        character_name = room_name[room_name.rfind('_') + 1:]

        # 使用 room_name 作为查询条件
        chat_history = ChatUserChatHistory.objects.filter(room_name=room_name).order_by('send_date')[:20]

        chat_info = [
            {
                "uid": message.uid,
                "username": message.username,
                "send_date": message.send_date.strftime('%b %d, %Y %I:%M%p'),
                "user_message": message.user_message
            } for message in chat_history
        ]

        return Response({
            "code": 0,
            "data": {
                "room_name": room_name,
                "room_id": room_id,
                "uid": uid,
                "username": character_name,
                "chat_info": chat_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticatedOrGuest])
def redirect_to_random_room(request):
    """
    随机选择一个正在直播的房间，并重定向到该房间的页面
    GET /api/live/redirect_to_random_room
    """
    try:
        keys = redis_client.keys('live_status:*')
        live_rooms = [key.decode('utf-8').replace('live_status:', '').replace(':', '_') for key in keys if redis_client.get(key) == b'start']

        if not live_rooms:
            return Response({"code": 1, "message": "No live rooms available."}, status=404)

        random_room_name = random.choice(live_rooms)
        collection = db[random_room_name]
        room_data = collection.find_one({"room_name": random_room_name})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        room_id = room_data.get("room_id")
        redirect_url = f"/live/{random_room_name}/{room_id}/"
        return redirect(redirect_url)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


def live_to_room(request, room_name, room_id):
    print("222222222222222")
    print(room_name)
    print(room_id)
    """渲染直播间页面"""
    return render(request, 'room_v3.html', {'room_name': room_name, 'room_id': room_id})


@api_view(['POST'])
@permission_classes([IsAuthenticatedOrGuest])
def save_user_chat_history(request):
    """
    保存用户聊天历史数据
    POST /api/live/save_user_chat_history
    """
    room_name = request.data.get("room_name")
    username = request.data.get("username")
    user_message = request.data.get("user_message")

    if not all([room_name, username, user_message]):
        return Response({"code": 1, "message": "缺少必填参数"}, status=400)

    try:
        if request.user.is_authenticated:
            username = request.user.username
            uid = str(request.user.id)
            identity = 1
        else:
            uid = "0"
            identity = 0

        ChatUserChatHistory.objects.create(
            room_name=room_name,
            uid=uid,
            username=username,
            user_message=user_message,
            send_date=timezone.now(),
            identity=identity
        )
        return Response({"code": 0, "message": "操作成功，聊天记录已保存"})

    except Exception as e:
        return Response({"code": 1, "message": f"服务器内部错误: {str(e)}"}, status=500)