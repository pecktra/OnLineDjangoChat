from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from chatApp.permissions import IsAuthenticatedOrGuest
from django_redis import get_redis_connection
from pymongo import MongoClient
from django.conf import settings
import json
import random
from django.shortcuts import redirect, render
from chatApp.models import ChatUserChatHistory,UserBalance,  RoomInfo, AnchorBalance,UserFollowedRoom, PaymentLiveroomEntryRecord,CharacterCard
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
from chatApp.consumers import ChatConsumer
from datetime import datetime, timedelta, timezone
from django.utils.dateparse import parse_datetime
import random
from math import ceil
from django.utils import timezone
# 获取 Redis 连接
redis_client = get_redis_connection('default')

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]


# 默认图片列表
default_images = [
    "headimage/default_image1.png",
    "headimage/default_image2.png"
]

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
    获取正在直播的直播间列表，支持 tags 搜索 + 分页
    GET /api/live/get_all_lives?tags=<tag>&page=<page>
    """
    # 获取 tags 参数
    search_tag = request.GET.get("tags", "").strip()
    page = int(request.GET.get("page", 1))  # 当前页，默认 1
    per_page = 12  # 每页 12 条

    # 1. 获取 Redis 中所有 uid
    uids = [key.decode('utf-8') if isinstance(key, bytes) else key for key in redis_client.keys('*')]
    if not uids:
        return Response({"code": 0, "data": {"lives_info": [], "page": page, "total_pages": 0, "total": 0}})

    # 2. 查询 RoomInfo 获取 room_id，只查 Redis 在线的
    room_infos = RoomInfo.objects.filter(room_id__in=uids)

    # 3. 如果有 tags 搜索，则过滤 room_infos
    if search_tag:
        filtered_room_ids = []
        for room_info in room_infos:
            character_card = CharacterCard.objects.filter(room_id=room_info.room_id).order_by('-create_date').first()
            if not character_card:
                continue

            if search_tag in ['en', 'cn']:
                if character_card.language == search_tag:
                    filtered_room_ids.append(room_info.room_id)
            else:
                if character_card.tags and search_tag in character_card.tags.split(','):
                    filtered_room_ids.append(room_info.room_id)

        room_infos = room_infos.filter(room_id__in=filtered_room_ids)

    live_status_list = []
    for room_info in room_infos:
        collection_name = room_info.room_id

        last_ai_doc = db[collection_name].find_one(
            {"data_type": "ai"},
            sort=[("data.send_date", -1)]
        )

        send_date_str = None
        if last_ai_doc and "data" in last_ai_doc:
            send_date_str = last_ai_doc["data"].get("send_date")

        character_card = CharacterCard.objects.filter(
            room_id=room_info.room_id
        ).order_by('-create_date').first()

        # ===== 修改部分：如果数据库没有图片就随机使用默认图片 =====
        if character_card:
            image_name = character_card.image_name
            image_path = character_card.image_path
        else:
            image_name = ""
            image_path = random.choice(default_images)
        # ============================================================

        online_count = ChatConsumer.get_online_count(room_info.room_id)

        live_status_list.append({
            "room_id": room_info.room_id,
            "room_name": room_info.room_name,
            "uid": room_info.uid,
            "username": room_info.user_name,
            "live_num": online_count,
            "character_name": room_info.character_name,
            "character_date": room_info.character_date,
            "image_name": image_name,
            "image_path": image_path,
            "tags": character_card.tags.split(",") if character_card and character_card.tags else [],
            "language": character_card.language if character_card else "en",
            "room_info": {
                "title": room_info.title or "",
                "describe": room_info.describe or "",
                "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                "room_type": room_info.room_type or 0
            },
            "last_ai_reply": send_date_str,
        })

    # 排序：按 last_ai_reply 降序，无 AI 回复排后面
    live_status_list.sort(
        key=lambda x: (
            x["last_ai_reply"] is None,
            -(parse_send_date(x["last_ai_reply"]).timestamp() if x["last_ai_reply"] else 0)
        )
    )

    # ===== 分页逻辑 =====
    total = len(live_status_list)
    total_pages = ceil(total / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_list = live_status_list[start:end]
    # ==================

    return Response({
        "code": 0,
        "data": {
            "lives_info": paginated_list,
            "page": page,
            "total_pages": total_pages,
            "total": total
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
def get_ranked_lives(request):
    """
    获取按照活跃度分数排序的正在直播的直播间列表
    GET /api/live/get_ranked_lives
    """
    try:
        # 1. 获取 Redis 中所有在线房间 UID
        uids = [key.decode('utf-8') if isinstance(key, bytes) else key for key in redis_client.keys('*')]
        if not uids:
            return Response({"code": 0, "status": "success", "data": {"lives_info": []}})

        room_infos = RoomInfo.objects.filter(room_id__in=uids)
        live_status_list = []

        now = datetime.utcnow()  # 使用 naive UTC datetime

        for room_info in room_infos:
            collection_name = room_info.room_id

            # 2. 获取最近一条 AI 回复
            last_ai_doc = db[collection_name].find_one(
                {"data_type": "ai"},
                sort=[("data.send_date", -1)]
            )

            send_date_str = None
            ai_reply_count = 0
            if last_ai_doc and "data" in last_ai_doc:
                send_date_str = last_ai_doc["data"].get("send_date")
                ai_reply_count = db[collection_name].count_documents({"data_type": "ai"})

            # 3. 获取角色卡
            character_card = CharacterCard.objects.filter(
                room_id=room_info.room_id
            ).order_by('-create_date').first()

            # ===== 修改部分：如果数据库没有图片就随机使用默认图片 =====
            if character_card:
                image_name = character_card.image_name
                image_path = character_card.image_path
            else:
                image_name = ""
                image_path = random.choice(default_images)
            # ============================================================

            # 4. 获取在线人数
            online_count = ChatConsumer.get_online_count(room_info.room_id)

            # 5. 计算最近回复加成
            recent_reply_bonus = 0
            if send_date_str:
                send_date = to_naive_datetime(send_date_str)
                if send_date:
                    diff = now - send_date
                    if diff < timedelta(minutes=5):
                        recent_reply_bonus = 10
                    elif diff < timedelta(minutes=30):
                        recent_reply_bonus = 5
                    elif diff < timedelta(hours=2):
                        recent_reply_bonus = 3

            # 6. 计算活跃度分数
            score = (online_count * 2) + (ai_reply_count * 1.5) + recent_reply_bonus

            # 7. 组装返回数据
            live_status_list.append({
                "room_id": room_info.room_id,
                "room_name": room_info.room_name,
                "uid": room_info.uid,
                "username": room_info.user_name,
                "live_num": online_count,
                "character_name": room_info.character_name,
                "character_date": room_info.character_date,
                "image_name": image_name,
                "image_path": image_path,
                "tags": character_card.tags.split(",") if character_card and character_card.tags else [],
                "language": character_card.language if character_card else "en",
                "room_info": {
                    "title": room_info.title or "",
                    "describe": room_info.describe or "",
                    "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                    "room_type": room_info.room_type or 0
                },
                "last_ai_reply": send_date_str,
                "ai_reply_count": ai_reply_count,
                "score": score
            })

        # 8. 按 score 降序排序
        live_status_list.sort(key=lambda x: x["score"], reverse=True)

        return Response({
            "code": 0,
            "status": "success",
            "data": {"lives_info": live_status_list}
        })

    except Exception as e:
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return Response({
            "code": 1,
            "status": "error",
            "message": str(e)
        }, status=500)


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
        room_info = RoomInfo.objects.filter(room_id=room_id).first()
        if not room_info:
            return Response({"code": 1, "message": "Room not found"}, status=404)

        status_str = redis_client.get(room_id)
        live_status = status_str.decode('utf-8').strip().lower() == "start" if status_str else False

        username = room_info.user_name

        vip_info = {
            "room_type": room_info.room_type,
            "vip_status": False,
            "amount": room_info.coin_num or 0
        }
        if vip_info["room_type"] != 0:
            vip_subscription = PaymentLiveroomEntryRecord.objects.filter(
                user_id=user.id,
                room_name=room_info.room_name
            ).first()
            if vip_subscription:
                vip_info["vip_status"] = True

        subscription_info = {
            "subscription_status": False,
            "amount": 0
        }
        redis_client_subscribe = get_redis_connection('subscribe')
        subscription_key = f"subscription:{user.id}:{room_info.uid}"
        subscription_data = redis_client_subscribe.get(subscription_key)
        if subscription_data:
            try:
                subscription_data = json.loads(subscription_data.decode('utf-8'))
                subscription_info["subscription_status"] = True
                subscription_info["amount"] = int(subscription_data.get("diamonds_paid", 0))
            except json.JSONDecodeError:
                print("Error decoding subscription data:", subscription_data)

        follow_info = {
            "follow_status": False
        }
        followed_room = UserFollowedRoom.objects.filter(user_id=user.id, room_id=room_info.room_id).first()
        if followed_room and followed_room.status:
            follow_info["follow_status"] = True

        character_card = CharacterCard.objects.filter(room_id=room_info.room_id).order_by('-create_date').first()
        if character_card:
            image_name = character_card.image_name
            image_path = character_card.image_path 
            tags = character_card.tags.split(",") if character_card.tags else []
            language = character_card.language or "en"
        else:
            image_name = ""
            image_path = random.choice(default_images)
            tags = []
            language = "en"

        # ✅ 计算最近一小时 AI 是否回复（MongoDB）
        collection_name = room_info.room_id
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)

        # 找最近一条 AI 回复
        last_ai_doc = db[collection_name].find_one(
            {"data_type": "ai"},
            sort=[("data.send_date", -1)]
        )

        ai_replied_recently = False
        if last_ai_doc and "data" in last_ai_doc:
            send_date_str = last_ai_doc["data"].get("send_date")
            if send_date_str:
                try:
                    # 解析 send_date
                    from datetime import datetime
                    try:
                        send_date = datetime.strptime(send_date_str, "%B %d, %Y %I:%M%p")
                    except ValueError:
                        send_date = datetime.strptime(send_date_str, "%Y-%m-%d %H:%M:%S")

                    send_date = timezone.make_aware(send_date, timezone.get_current_timezone())
                    if send_date >= one_hour_ago:
                        ai_replied_recently = True
                except Exception as e:
                    print(f"Error parsing send_date: {e}")

        live_info = {
            "room_id": room_info.room_id,
            "room_name": room_info.room_name,
            "uid": room_info.uid,
            "username": username,
            "character_name": room_info.character_name,
            "image_name": image_name,
            "image_path": image_path,
            "tags": tags,
            "language": language,
            "live_status": live_status,
            "title": room_info.title,
            "describe": room_info.describe,
            "live_num": ChatConsumer.get_online_count(room_info.room_id),
            "ai_replied_recently": ai_replied_recently  # ✅ 新增字段
        }

        return Response({
            "code": 0,
            "data": {
                "live_info": live_info,
                "vip_info": vip_info,
                "follow_info": follow_info,
                "subscription_info": subscription_info
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


@api_view(['GET'])
def get_all_tags(request):
    """
    获取所有角色卡标签，语言本身也作为标签，去掉 NSFW 标签
    GET /api/card/get_all_tags/
    """
    try:
        cards = CharacterCard.objects.all().values('language', 'tags')
        all_tags = set()
        nsfw_keywords = {"Not Safe for Work", "NotSafeforWork", "NSFW", "nsfw"}

        for card in cards:
            language = card['language'] or 'en'
            all_tags.add(language)  # 将语言本身作为标签

            tags_str = card['tags'] or ''
            tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

            # 过滤 NSFW 标签
            tags_list = [tag for tag in tags_list if tag not in nsfw_keywords]

            all_tags.update(tags_list)

        return JsonResponse({
            "code": 0,
            "status": "success",
            "tags": sorted(list(all_tags))
        })

    except Exception as e:
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return JsonResponse({
            "code": 1,
            "status": "error",
            "message": str(e)
        }, status=500)