from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from chatApp.permissions import IsAuthenticatedOrGuest
from django_redis import get_redis_connection
from pymongo import MongoClient
from django.conf import settings
import json
import random
from django.shortcuts import redirect, render
from chatApp.models import ChatUserChatHistory,UserBalance,  RoomInfo, AnchorBalance,UserFollowedRoom, PaymentLiveroomEntryRecord
from django.utils import timezone
from django.db.models import Subquery, OuterRef
import hashlib
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db import transaction
from datetime import timedelta
from django.contrib.auth import get_user
from django.http import JsonResponse
import chatProject.settings as setting
from datetime import datetime

# 获取 Redis 连接
redis_client = get_redis_connection('default')

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]


def parse_send_date(send_date_str):
    """
    将 MongoDB 中的 send_date 字符串解析为 datetime 对象
    例如 "September 12, 2025 10:30pm" 或 "2025-09-12 22:30:00"
    """
    if not send_date_str:
        return None
    try:
        return datetime.strptime(send_date_str, "%B %d, %Y %I:%M%p")
    except ValueError:
        try:
            return datetime.strptime(send_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

@api_view(['GET'])
def get_all_lives(request):
    """
    获取正在直播的直播间列表
    GET /api/live/get_all_lives
    按最近 AI 回复时间 (data.send_date) 降序排序，没有 AI 回复的排后面
    从 Redis 获取 uid，查询 RoomInfo 获取 room_id，直接查询 MongoDB
    """
    # 1. 获取 Redis 中所有 uid
    uids = [key.decode('utf-8') if isinstance(key, bytes) else key for key in redis_client.keys('*')]

    # 2. 查询 RoomInfo 获取 room_id
    room_infos = RoomInfo.objects.filter(room_id__in=uids)

    live_status_list = []
    for room_info in room_infos:
        collection_name = room_info.room_id  # 每个房间对应的集合名
        # 查询对应集合中最新 AI 回复
        last_ai_doc = db[collection_name].find_one(
            {"data_type": "ai"},
            sort=[("data.send_date", -1)]
        )

        send_date_str = None
        if last_ai_doc and "data" in last_ai_doc:
            send_date_str = last_ai_doc["data"].get("send_date")

        live_status_list.append({
            "room_id": room_info.room_id,
            "room_name": room_info.room_name,
            "uid": room_info.uid,
            "username": room_info.user_name,
            "live_num": 0,
            "character_name": room_info.character_name,
            "character_date": room_info.character_date,
            "room_info": {
                "title": room_info.title or "",
                "describe": room_info.describe or "",
                "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                "room_type": room_info.room_type or 0
            },
            "last_ai_reply": send_date_str
        })

    # 4. 排序：按 last_ai_reply 降序，无 AI 回复的排后面
    live_status_list.sort(
        key=lambda x: (
            x["last_ai_reply"] is None,
            -(parse_send_date(x["last_ai_reply"]).timestamp() if x["last_ai_reply"] else 0)
        )
    )

    return Response({
        "code": 0,
        "data": {"lives_info": live_status_list}
    })

@api_view(['GET'])
def get_live_info(request):
    """
    获取单个直播间信息
    GET /api/live/get_live_info?room_id=<room_id>
    """
    room_id = request.GET.get("room_id")

    user = get_user(request)
    if not room_id:
        return Response({"code": 1, "message": "Missing room_name parameter"}, status=400)

    try:
        # 先从 RoomInfo 获取房间信息
        room_info = RoomInfo.objects.filter(room_id=room_id).first()

        # 检查 room_info 是否为空
        if not room_info:
            return Response({"code": 1, "message": "Room not found"}, status=404)

        # 获取 live_status
        status_str = redis_client.get(room_id)
        live_status = status_str.decode('utf-8').strip().lower() == "start" if status_str else False

        username = room_info.user_name

        # 处理 VIP 信息
        vip_info = {
            "room_type": room_info.room_type,
            "vip_status": False,  # 默认为 False
            "amount": room_info.coin_num
        }

        if not room_info.coin_num:
            vip_info['amount'] = 0

        # 如果是 VIP 房间（即 room_type 为 1），并且用户已经订阅了此房间
        if vip_info["room_type"] != 0:  # 如果不是免费房间
            vip_subscription = VipSubscriptionRecord.objects.filter(user_id=user.id,
                                                                    room_name=room_info.room_name).first()

            if vip_subscription:
                # 订阅有效，设置 vip_status 为 True
                vip_info["vip_status"] = True

        # 获取订阅信息
        subscription_info = {
            "subscription_status": False,  # 默认为未订阅
            "amount": 0  # 默认为 0
        }

        # 查询用户是否订阅了该主播的任何直播间
        redis_client_subscribe = get_redis_connection('subscribe')
        subscription_key = f"subscription:{user.id}:{room_info.uid}"  # 使用 user.id 和 uid 作为键
        subscription_data = redis_client_subscribe.get(subscription_key)

        if subscription_data:
            # 如果从 Redis 获取到的数据是 bytes 类型，先进行解码
            try:
                # 假设订阅数据是 JSON 格式
                subscription_data = json.loads(subscription_data.decode('utf-8'))
                subscription_info["subscription_status"] = True
                subscription_info["amount"] = int(subscription_data.get("diamonds_paid", 0))
            except json.JSONDecodeError:
                # 如果 JSON 解码失败，可以输出一些调试信息
                print("Error decoding subscription data:", subscription_data)
                subscription_info["subscription_status"] = False

        # 获取 follow_info
        follow_info = {
            "follow_status": False  # 默认为未关注
        }

        # 查询是否已关注
        followed_room = UserFollowedRoom.objects.filter(user_id=user.id, room_id=room_info.room_id).first()
        if followed_room and followed_room.status:
            follow_info["follow_status"] = True  # 用户已关注

        # 构建返回的 live_info
        live_info = {
            "room_id": room_info.room_id,
            "room_name": room_info.room_name,
            "uid": room_info.uid,
            "username": username,
            "character_name": room_info.character_name,
            "live_status": live_status,
            "title": room_info.title,
            "describe": room_info.describe
        }

        return Response({
            "code": 0,
            "data": {
                "live_info": live_info,
                "vip_info": vip_info,
                "follow_info": follow_info,
                "subscription_info": subscription_info  # 添加订阅信息
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
def get_live_chat_history(request):
    """
    获取当前直播间主播历史消息数据
    GET /api/live/get_live_chat_history?room_name=<room_name>
    """
    room_id = request.GET.get("room_id")
    if not room_id:
        return Response({"code": 1, "message": "Missing room_id"}, status=400)

    try:
        # 使用 room_name 访问集合
        collection = db[room_id]
        room_data = collection.find_one({"room_id": room_id})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        # # 提取 uid 和 character_name
        # uid = room_name[:room_name.rfind('_')]
        # character_name = room_name[room_name.rfind('_') + 1:]

        # 使用 room_id 访问聊天数据集合
        collection = db.get_collection(room_id)
        chat_history = collection.find()

        # 获取主播的 username（从 room_data 中提取）
        username = room_data.get("username")
        room_name = room_data.get("room_name")
        uid = room_data.get("uid")
        # 格式化聊天历史
        chat_info = []
        for message in chat_history:
            data = message.get("data", {})
            live_message = data.get("mes")
            live_message_html = message.get("mes_html","")
            send_date = data.get("send_date")
            message_username = data.get("name", "Unknown")
            is_user = data.get("is_user", False)

            sender_name = message_username if is_user else message.get("character_name", "ai")
            chat_info.append({
                "is_user": is_user,
                "live_message": live_message,
                "live_message_html":live_message_html,
                "sender_name": sender_name,
                "send_date": send_date
            })


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
def get_user_chat_history(request):
    """
    获取当前直播间用户历史消息数据
    GET /api/live/get_user_chat_history?room_id=<room_id>
    """
    room_id = request.GET.get("room_id")
    if not room_id:
        return Response({"code": 1, "message": "Missing room_id"}, status=400)

    try:
        # 获取房间数据
        collection = db[room_id]
        room_data = collection.find_one({"room_id": room_id})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)


        character_name = room_data.get("character_name")
        uid = room_data.get("uid")
        room_name = room_data.get("room_name")

        # 使用 room_name 作为查询条件
        chat_history = ChatUserChatHistory.objects.raw("""
            SELECT * 
            FROM (
                SELECT * 
                FROM chatApp_chatuser_chat_history 
                WHERE room_id = %s 
                ORDER BY send_date DESC 
                LIMIT 50
            ) AS subquery 
            ORDER BY send_date ASC
        """, [room_id])

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
def redirect_to_random_room(request):
    """
    随机选择一个正在直播的房间，并重定向到该房间的页面
    GET /api/live/redirect_to_random_room
    """
    try:
        # 获取所有 key
        keys = redis_client.keys('*')  # '*' 匹配所有 key

        # 转换为字符串列表
        live_rooms = [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        if not live_rooms:
            return Response({"code": 1, "message": "No live rooms available."}, status=404)

        random_room_id = random.choice(live_rooms)
        collection = db[random_room_id]
        room_data = collection.find_one({"room_id": random_room_id})

        if not room_data:
            return Response({"code": 1, "message": "Room not found in database."}, status=404)

        room_id = room_data.get("room_id")
        redirect_url = f"/live/{room_id}/"
        return redirect(redirect_url)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


def live_to_room(request,  room_id):

    """渲染直播间页面"""
    return render(request, 'live.html', {'room_id': room_id , "build_universe_url":setting.build_universe_url})



def home_view(request):
    return render(request, 'home.html', {'room_id': None, "build_universe_url":setting.build_universe_url})


@api_view(['POST'])
def save_user_chat_history(request):
    """
    保存用户聊天历史数据
    POST /api/live/save_user_chat_history
    """

    user = get_user(request)  # 获取当前用户

    if not user:
        return JsonResponse({"code": 1, "message": "User not authenticated"}, status=400)

    room_id = request.data.get("room_id")
    room_name = request.data.get("room_name")
    username = request.data.get("username")
    user_message = request.data.get("user_message")

    if not all([room_id,room_name, username, user_message]):
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
            room_id = room_id,
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



@api_view(['POST'])
def pay_vip_coin(request):
    """
    用户支付 VIP 钻石，记录到 PaymentLiveroomEntryRecord
    POST /api/live/pay_vip_coin
    """
    user_id = request.data.get('user_id')
    room_name = request.data.get('room_name')  # 房间名
    pay_coin_num = request.data.get('amount')
    anchor_id = request.data.get('anchor_id')

    # 参数验证
    if not user_id or not room_name or pay_coin_num is None or not anchor_id:
        return Response({"code": 1, "message": "Missing required parameters"}, status=400)

    try:
        pay_coin_num = Decimal(pay_coin_num)

        # 获取用户余额
        user_balance = get_object_or_404(UserBalance, user_id=user_id)
        if user_balance.balance < pay_coin_num:
            return Response({"code": 1, "message": "Insufficient balance"}, status=400)

        # 获取主播余额记录，如果没有则创建
        anchor_balance, _ = AnchorBalance.objects.get_or_create(
            anchor_id=anchor_id,
            defaults={'balance': Decimal(0), 'total_received': Decimal(0)}
        )

        # 计算 crypto_amount，按 5:1 比例
        crypto_amount = pay_coin_num / Decimal(5)

        with transaction.atomic():
            # 扣除用户余额
            user_balance.balance -= pay_coin_num
            user_balance.save()

            # 增加主播余额
            anchor_balance.balance += pay_coin_num
            anchor_balance.total_received += pay_coin_num
            anchor_balance.save()

            # 创建直播间进入记录
            entry_record = PaymentLiveroomEntryRecord.objects.create(
                user_id=user_id,
                anchor_id=anchor_id,
                room_name=room_name,
                amount=pay_coin_num,
                currency="USD",
                crypto_amount=crypto_amount,
                crypto_currency="USDT"
            )

        # 返回值保持原接口格式
        return Response({
            "code": 0,
            "message": "VIP payment successful",
            "data": {
                "user_id": user_id,
                "room_name": room_name,
                "anchor_id": anchor_id,
                "pay_coin_num": float(pay_coin_num),
                "entry_date": entry_record.id,  # 用 id 代替时间字段
                "remaining_balance": float(user_balance.balance)
            }
        }, status=200)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)