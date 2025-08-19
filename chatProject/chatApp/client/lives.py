from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from chatApp.permissions import IsAuthenticatedOrGuest
from django_redis import get_redis_connection
from pymongo import MongoClient
from django.conf import settings
import json
import random
from django.shortcuts import redirect, render
from chatApp.models import ChatUserChatHistory,UserBalance,  RoomInfo, AnchorBalance, VipSubscriptionRecord,UserFollowedRoom
from django.utils import timezone
from django.db.models import Subquery, OuterRef
import hashlib
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db import transaction
from datetime import timedelta
from django.contrib.auth import get_user
from django.http import JsonResponse


# 获取 Redis 连接
redis_client = get_redis_connection('default')

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# 直播间相关 API
@api_view(['GET'])
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

                if status_str and status_str.decode('utf-8') == "start":
                    # 生成房间 ID
                    room_id = hashlib.md5(collection_name.encode('utf-8')).hexdigest()

                    # 获取 live_num
                    live_num = user.get("live_num", 0)

                    # 获取房间信息（从 Redis 中获取）
                    room_key = f"room_info:{uid}:{character_name}"
                    room_info = redis_client.get(room_key)

                    live_status_list.append({
                        "room_name": collection_name,
                        "room_id": room_id,
                        "uid": uid,
                        "username": username,
                        "live_num": live_num,
                        "character_name": character_name,
                        "room_info": room_info  # 添加房间信息
                    })

        return Response({
            "code": 0,
            "data": {"lives_info": live_status_list}
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
def get_live_info(request):
    """
    获取单个直播间信息
    GET /api/live/get_live_info?room_name=<room_name>
    """
    room_name = request.GET.get("room_name")

    user = get_user(request)
    if not room_name:
        return Response({"code": 1, "message": "Missing room_name parameter"}, status=400)

    try:
        # 从 RoomInfo 获取数据
        uid = room_name.rsplit('_', 1)[0]
        character_name = room_name.rsplit('_', 1)[1]

        # 先从 RoomInfo 获取房间信息
        try:
            room_info = RoomInfo.objects.get(uid=uid, character_name=character_name)
        except RoomInfo.DoesNotExist:
            # 如果在 RoomInfo 中没有找到该房间，先尝试从 MongoDB 查找
            collection = db[room_name]  # 使用 room_name 直接访问集合
            room_data_from_mongo = collection.find_one({"room_name": room_name})
            if room_data_from_mongo:
                # 如果 MongoDB 中有该房间，直接返回构造的房间信息（不写入数据库）
                room_info = {
                    "uid": uid,
                    "character_name": character_name,
                    "title": "",  # 默认 title 为空
                    "coin_num": 0,  # 默认 coin_num 为 0
                    "room_type": 0  # 默认 room_type 为 0 (Free)
                }
            else:
                # 如果 MongoDB 中也没有该房间，则返回错误
                return Response({"code": 1, "message": "Room does not exist."}, status=404)

        # 获取 live_status
        live_key = f"live_status:{uid}:{character_name}"
        status_str = redis_client.get(live_key)
        live_status = status_str.decode('utf-8').strip().lower() == "start" if status_str else False

        # 获取用户信息，直接从 room_data 中获取
        collection = db[room_name]
        room_data = collection.find_one({"room_name": room_name})
        username = room_data.get("username", "Unknown")

        # 处理 VIP 信息
        vip_info = {
            "room_type": room_info['room_type'] if isinstance(room_info, dict) else room_info.room_type,
            "vip_status": False,  # 默认为 False
            "amount": room_info['coin_num'] if isinstance(room_info, dict) else room_info.coin_num
        }

        # 如果是 VIP 房间（即 room_type 为 1），并且用户已经订阅了此房间
        if vip_info["room_type"] != 0:  # 如果不是免费房间
            vip_subscription = VipSubscriptionRecord.objects.filter(user_id=user.id, room_name=room_name).first()

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
        subscription_key = f"subscription:{user.id}:{uid}"  # 使用 user.id 和 uid 作为键
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
        followed_room = UserFollowedRoom.objects.filter(user_id=user.id, room_name=room_name).first()
        if followed_room and followed_room.status:
            follow_info["follow_status"] = True  # 用户已关注

        # 构建返回的 live_info
        live_info = {
            "room_name": room_name,
            "uid": uid,
            "username": username,
            "character_name": character_name,
            "live_status": live_status,
            "title": room_info['title'] if isinstance(room_info, dict) else room_info.title
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
        chat_history = ChatUserChatHistory.objects.raw("""
            SELECT * 
            FROM (
                SELECT * 
                FROM chatApp_chatuser_chat_history 
                WHERE room_name = %s 
                ORDER BY send_date DESC 
                LIMIT 50
            ) AS subquery 
            ORDER BY send_date ASC
        """, [room_name])

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

    """渲染直播间页面"""
    return render(request, 'room_v3.html', {'room_name': room_name, 'room_id': room_id})


@api_view(['POST'])
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



@api_view(['POST'])
def pay_vip_coin(request):
    """
    用户支付 VIP 钻石
    POST /api/live/pay_vip_coin
    """
    # 获取请求参数
    user_id = request.data.get('user_id')  # 用户id
    room_name = request.data.get('room_name')  # 房间名
    pay_coin_num = request.data.get('amount')  # 支付的钻石数量
    anchor_id = request.data.get('anchor_id')  # 主播id

    # 参数验证
    if not user_id or not room_name or pay_coin_num is None or not anchor_id:
        return Response({"code": 1, "message": "Missing required parameters"}, status=400)

    try:
        # 确保 pay_coin_num 是 Decimal 类型
        pay_coin_num = Decimal(pay_coin_num)  # 转换 pay_coin_num 为 Decimal 类型

        # 获取用户余额
        user_balance = get_object_or_404(UserBalance, user_id=user_id)

        # 检查用户余额是否足够支付
        if user_balance.balance < pay_coin_num:
            return Response({"code": 1, "message": "Insufficient balance"}, status=400)

        # 获取房间信息
        room_info = RoomInfo.objects.filter(uid=anchor_id).first()  # 先尝试查找，若没有返回 None
        if not room_info:
            return Response({"code": 1, "message": "RoomInfo not found for the user."}, status=404)

        # 获取主播信息（通过 anchor_id 获取 AnchorBalance）
        try:
            # 尝试通过 anchor_id 查找 AnchorBalance 记录
            anchor_balance = AnchorBalance.objects.get(anchor_id=anchor_id)
        except AnchorBalance.DoesNotExist:
            # 如果没有找到对应的 AnchorBalance，创建一个新的 AnchorBalance 记录，余额和总打赏金额初始化为 0
            anchor_balance = AnchorBalance.objects.create(anchor_id=anchor_id, balance=Decimal(0), total_donations=Decimal(0))

        # 检查是否已经订阅过该主播和该直播间
        existing_subscription = VipSubscriptionRecord.objects.filter(user_id=user_id, anchor_id=anchor_id,
                                                                     room_name=room_name).first()
        # 如果用户已经订阅过该主播，返回错误信息
        if existing_subscription:
            return JsonResponse({"code": 1, "message": "You have already subscribed to this anchor."}, status=400)

        # 进入事务处理，确保支付、余额扣除和增加操作是原子的
        with transaction.atomic():
            # 扣除用户余额
            user_balance.deduct_balance(pay_coin_num)

            # 增加主播的余额
            anchor_balance.balance += pay_coin_num
            anchor_balance.total_donations += pay_coin_num  # 可选，记录主播收到的总打赏金额
            anchor_balance.save()


            # 创建 VipSubscriptionRecord 记录支付信息
            vip_subscription_record = VipSubscriptionRecord.objects.create(
                user_id=user_id,
                anchor_id=anchor_id,
                room_name=room_name,  # 将 room_name 存储到表中
                pay_coin_num=pay_coin_num,
                subscription_date=timezone.now(),
            )
        # 返回成功响应
        return Response({"code": 0, "message": "VIP payment successful"}, status=200)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)