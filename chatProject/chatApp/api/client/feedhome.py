import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from pymongo import MongoClient
from datetime import datetime
from pytz import UTC
from django.conf import settings
from chatApp.models import RoomInfo, ChatUser, CharacterCard
from chatApp.api.common.common import build_full_image_url
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated


# ---------- 分页类 ----------
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ---------- 工具函数 ----------
def safe_parse_json(data_raw):
    if isinstance(data_raw, str):
        if not data_raw.strip():
            return {}
        try:
            return json.loads(data_raw)
        except json.JSONDecodeError:
            return {}
    return data_raw


# ---------- 通用信息流函数 ----------
def _fetch_feed_rooms(request, personal_only=False):
    redis_conn = get_redis_connection("default")

    # Redis Key 设计
    if personal_only:
        user_id = request.user.id
        cache_key = f"personal_feed:{user_id}"
    else:
        cache_key = "feed:all"

    # 尝试读取缓存
    cached_data = redis_conn.get(cache_key)
    if cached_data:
        cached_json = json.loads(cached_data)
        paginator = StandardResultsSetPagination()
        page_obj = paginator.paginate_queryset(cached_json, request)
        return Response({
            "code": 0,
            "message": "Success",
            "data": {
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": page_obj
            }
        })

    # ---------- 没有缓存，生成数据 ----------
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    rooms_query = RoomInfo.objects.filter(is_show=0, file_branch="branch").order_by('-created_at')
    if personal_only:
        rooms_query = rooms_query.filter(uid=request.user.id)

    result = []

    for room in rooms_query:
        collection = db[room.room_id]

        # 查找该房间中第一个用户消息（data.is_user == True），按 _id 升序
        try:
            first_user_doc = collection.find_one({"data.is_user": True}, sort=[("_id", 1)])
        except Exception:
            # 如果数据结构不满足查询条件，尝试退回到最早文档
            first_user_doc = collection.find_one({}, sort=[("_id", 1)])

        if not first_user_doc:
            continue

        data_dict = safe_parse_json(first_user_doc.get("data", {}))

        send_date_str = data_dict.get("send_date")
        if send_date_str:
            try:
                dt_obj = datetime.strptime(send_date_str, "%B %d, %Y %I:%M%p").astimezone(UTC)
                iso_send_date = dt_obj.isoformat(timespec='seconds') + 'Z'
            except Exception:
                iso_send_date = ""
        else:
            iso_send_date = ""

        filtered_data = {
            "name": data_dict.get("name"),
            "is_user": data_dict.get("is_user", 0),
            "send_date": iso_send_date,
            "mes": data_dict.get("mes"),
        }

        # 获取房主信息
        try:
            user_obj = ChatUser.objects.get(id=room.uid)
            user_info = {
                "username": user_obj.username,
                "nickname": getattr(user_obj, "nickname", "") or "",
                "avatar": getattr(user_obj, "avatar", "") or ""
            }
        except ChatUser.DoesNotExist:
            user_info = {
                "username": room.user_name or "",
                "nickname": "",
                "avatar": ""
            }

        # 使用新的 build_full_image_url 签名 (uid, room_id)
        image_info = build_full_image_url(request, uid=room.uid, room_id=room.room_id)

        card_info = {
            "room_id": room.room_id,
            "character_name": room.character_name,
            "image": image_info['image_path'],
            "title": room.title,
            "describe": room.describe,
            "file_branch": room.file_branch,
            "first_user_message": filtered_data,
            "data_type": first_user_doc.get("data_type"),
            "mes_html": first_user_doc.get("mes_html", ""),
        }

        result.append({
            "user": user_info,
            "card": card_info
        })

    # ---------- 缓存结果到 Redis，设置过期时间（例如 60 秒） ----------
    try:
        redis_conn.set(cache_key, json.dumps(result, default=str), ex=60)
    except Exception:
        # 缓存失败不影响主流程
        pass

    # ---------- 分页 ----------
    paginator = StandardResultsSetPagination()
    page_obj = paginator.paginate_queryset(result, request)

    return Response({
        "code": 0,
        "message": "Success",
        "data": {
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": page_obj
        }
    })

# ---------- 全量信息流接口 ----------
@api_view(['GET'])
def get_feed_rooms(request):
    return _fetch_feed_rooms(request, personal_only=False)


# ---------- 个人信息流接口 ----------
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_personal_feed(request):
    return _fetch_feed_rooms(request, personal_only=True)
