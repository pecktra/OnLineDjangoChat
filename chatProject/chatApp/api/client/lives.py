from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_redis import get_redis_connection
from pymongo import MongoClient
from django.conf import settings
import json
from django.shortcuts import redirect, render
from chatApp.models import ChatUserChatHistory, UserBalance, RoomInfo, AnchorBalance, PaymentLiveroomEntryRecord, \
    ChatUser, CharacterCard,UserFollowRelation,RoomImageBinding,Favorite
from django.utils import timezone
from datetime import datetime
from django.db.models import Subquery, OuterRef
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user
from django.http import JsonResponse
from chatApp.consumers import ChatConsumer
from django.utils.dateparse import parse_datetime
from chatApp.api.common.common import  build_full_image_url, IDCursorPagination
from chatApp.api.common.payment import process_diamond_payment
from rest_framework.pagination import CursorPagination
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

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
    获取正在直播的直播间列表，支持 tags 搜索 + CursorPagination
    GET /api/live/get_all_lives?tags=萝莉&cursor=xxx
    """
    raw_tag = request.GET.get("tags", "").strip()
    search_tag = raw_tag.lower() if raw_tag else None  # 统一转小写用于匹配

    # 1. 查询公开房间
    room_infos = RoomInfo.objects.filter(is_show=0, file_branch='main')

    # 2. 更新每个 room 的 last_ai_reply_timestamp（你原来的逻辑保留）
    for room in room_infos:
        collection = db[room.room_id]
        last_ai_doc = collection.find_one(
            {"data_type": "ai"},
            sort=[("data.send_date", -1)]
        )
        if last_ai_doc and "data" in last_ai_doc:
            send_date_str = last_ai_doc["data"].get("send_date")
            dt = parse_send_date(send_date_str)
            if dt:
                timestamp = dt.timestamp()
                if room.last_ai_reply_timestamp != timestamp:
                    RoomInfo.objects.filter(pk=room.pk).update(last_ai_reply_timestamp=timestamp)

    # 3. 分页（你原来的分页方式完全保留）
    paginator = IDCursorPagination()
    paginator.ordering = ['-weight', '-last_ai_reply_timestamp']
    paginated_rooms = paginator.paginate_queryset(room_infos, request)

    # 4. 构建返回数据（超级简洁！所有复杂逻辑都在 build_full_image_url 里）
    lives_info = []
    for room in paginated_rooms:
        image_info = build_full_image_url(
            request, room.uid, room.room_id, search_tag
        )

        # 判断是否被过滤：超级容易！
        if not image_info["image_name"]:  # 没名字 = 被过滤了
            continue

        lives_info.append({
            "room_id": room.room_id,
            "room_name": room.room_name,
            "uid": room.uid,
            "username": room.user_name,
            "character_name": room.character_name,
            "character_date": room.character_date,
            "image_name": image_info['image_name'],
            "image_path": image_info['image_path'],
            "tags": image_info['tags'],  # 原始字符串
            "language": image_info['language'],
            "room_info": {
                "title": room.title or "",
                "describe": room.describe or "",
                "coin_num": room.coin_num if room.coin_num is not None else 0,
                "room_type": room.room_type or 0
            },
            "last_ai_reply_timestamp": room.last_ai_reply_timestamp,
            "weight": room.weight
        })

    # 5. 分页链接（你原来的写法完全保留）
    next_link = paginator.get_next_link()
    previous_link = paginator.get_previous_link()

    if next_link:
        next_link = request.build_absolute_uri(next_link)
    if previous_link:
        previous_link = request.build_absolute_uri(previous_link)

    # 6. 返回
    return Response({
        "code": 0,
        "message": "Success",
        "data": {
            "next": next_link,
            "previous": previous_link,
            "results": lives_info
        }
    })


def to_naive_datetime(send_date_str):
    """
    将 send_date 字符串转换为 naive datetime，确保无论带不带时区都可以比较。
    """
    if not send_date_str:
        return None
    try:
        dt = parse_datetime(send_date_str)
        if dt is None:
            # 尝试手动解析 ISO 格式
            dt = datetime.fromisoformat(send_date_str.replace("Z", "+00:00"))
    except Exception:
        return None

    # 转为 naive datetime（去掉 tzinfo）
    if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


@api_view(['GET'])
def get_live_info(request):
    """
    获取单个直播间信息（可未登录访问）
    GET /api/live/get_live_info?room_id=<room_id>
    """

    room_id = request.GET.get("room_id")

    # 尝试获取用户，但不强制要求
    try:
        user = get_user(request)
        is_authenticated = True
    except:
        user = None
        is_authenticated = False

    if not room_id:
        return Response({"code": 1, "message": "Missing room_id parameter"}, status=400)

    try:
        room_info = RoomInfo.objects.filter(room_id=room_id).first()
        if not room_info:
            return Response({"code": 1, "message": "Room not found"}, status=404)

        username = room_info.user_name

        # VIP 信息（未登录：全部返回默认值）
        vip_info = {
            "room_type": room_info.room_type,
            "vip_status": False,
            "amount": room_info.coin_num or 0
        }

        if is_authenticated and room_info.room_type != 0:
            vip_subscription = PaymentLiveroomEntryRecord.objects.filter(
                user_id=user.id,
                room_name=room_info.room_name
            ).first()
            if vip_subscription:
                vip_info["vip_status"] = True

        # 订阅信息（未登录：默认 0）
        subscription_info = {"subscription_status": False, "amount": 0}

        if is_authenticated:
            redis_client_subscribe = get_redis_connection('subscribe')
            subscription_key = f"subscription:{user.id}:{room_info.uid}"
            subscription_data = redis_client_subscribe.get(subscription_key)
            if subscription_data:
                try:
                    subscription_data = json.loads(subscription_data.decode('utf-8'))
                    subscription_info["subscription_status"] = True
                    subscription_info["amount"] = int(subscription_data.get("diamonds_paid", 0))
                except json.JSONDecodeError:
                    pass  # 忽略解析错误

        image_info = build_full_image_url(request, uid=room_info.uid, room_id=room_info.room_id)

        # AI 最近一小时是否回复
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        ai_replied_recently = False
        if room_info.last_ai_reply_timestamp:
            last_ai_time = datetime.fromtimestamp(
                room_info.last_ai_reply_timestamp,
                tz=timezone.get_current_timezone()
            )
            if last_ai_time >= one_hour_ago:
                ai_replied_recently = True

        # 收藏状态（未登录：返回 0）
        favorite_status = 0
        if is_authenticated:
            favorite = Favorite.objects.filter(uid=user.id, room_id=room_id, status=1).first()
            if favorite:
                favorite_status = 1

        favorite_info = {"favorite_status": favorite_status}

        # 关注状态（未登录：False）
        follow_status = False
        if is_authenticated:
            follow_relation = UserFollowRelation.objects.filter(
                follower_id=str(user.id),
                followed_id=str(room_info.uid),
                status=True
            ).first()
            if follow_relation:
                follow_status = True

        follow_info = {"follow_status": follow_status}

        nickname = ""
        if is_authenticated:
            chat_user = ChatUser.objects.filter(id=user.id).first()
            if chat_user and chat_user.nickname:
                nickname = chat_user.nickname

        live_info = {
            "room_id": room_info.room_id,
            "room_name": room_info.room_name,
            "uid": room_info.uid,
            "username": username,
            "nickname": nickname,
            "character_name": room_info.character_name,
            "image_name": image_info['image_name'],
            "image_path": image_info['image_path'],
            "tags": image_info['tags'],
            "language": image_info['language'],
            "title": room_info.title,
            "describe": room_info.describe,
            "live_num": ChatConsumer.get_online_count(room_info.room_id),
            "ai_replied_recently": ai_replied_recently
        }

        return Response({
            "code": 0,
            "data": {
                "live_info": live_info,
                "vip_info": vip_info,
                "subscription_info": subscription_info,
                "follow_info": follow_info,
                "favorite_info": favorite_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


class ChatHistoryPagination(PageNumberPagination):
    page_size = 10  # 每页返回的条目数
    page_size_query_param = 'page_size'  # 可选的分页大小参数
    max_page_size = 100  # 最大页大小


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

        # 使用 room_name 作为查询条件
        chat_history = ChatUserChatHistory.objects.raw("""
                                                       SELECT *
                                                       FROM (SELECT *
                                                             FROM chatApp_chatuser_chat_history
                                                             WHERE room_id = %s
                                                             ORDER BY send_date DESC LIMIT 50) AS subquery
                                                       ORDER BY send_date DESC
                                                       """, [room_id])

        # 分页处理
        paginator = ChatHistoryPagination()
        paginated_chat_history = paginator.paginate_queryset(chat_history, request)

        # 获取聊天记录和处理每个消息的时间和昵称
        chat_info = []
        for message in paginated_chat_history:
            # 获取用户昵称
            user = ChatUser.objects.filter(id=message.uid).first()
            message_nickname = user.nickname if user else ""  # 如果找不到用户，返回空字符串

            # # 格式化时间为 UTC 格式

            send_date = message.send_date.astimezone(timezone.get_current_timezone())

            # 格式化时间为 UTC 格式
            send_date = send_date.isoformat() + 'Z'

            chat_info.append({
                "uid": message.uid,
                "username": message.username,
                "nickname": message_nickname,  # 获取对应的昵称
                "send_date": send_date,
                "user_message": message.user_message
            })

        return Response({
            "code": 0,
            "message": "Success",
            "data":{
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": chat_info
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 确保只有认证用户可以访问
def save_user_chat_history(request):
    """
    保存用户聊天历史数据
    POST /api/live/save_user_chat_history
    """

    # 当前用户信息通过 request.user 获取
    user = request.user

    room_id = request.data.get("room_id")
    user_message = request.data.get("user_message")

    if not all([room_id, user_message]):
        return Response({"code": 1, "message": "缺少必填参数"}, status=400)

    try:
        # 使用 request.user 获取认证的用户信息
        uid = str(user.id)  # 用户 ID
        username = user.username  # 用户名

        # 获取房间名称
        room_info = RoomInfo.objects.filter(room_id=room_id).first()
        if not room_info:
            return Response({"code": 1, "message": "房间未找到"}, status=404)

        room_name = room_info.room_name  # 获取房间名

        # identity 设置为 1，因为用户是认证过的
        identity = 1

        # 创建聊天记录
        ChatUserChatHistory.objects.create(
            room_id=room_id,
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

        expenditure_record = process_diamond_payment(
            user_id=user_id,
            anchor_id=anchor_id,
            amount=pay_coin_num,
            payment_type='room_entry',  # ✅ 指明类型
            payment_source='room_entry',  # ✅ 保留字段
            details=f"进入VIP房间 {room_name}（主播ID: {anchor_id}）"
        )

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


