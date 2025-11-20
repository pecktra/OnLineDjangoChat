from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime, timezone
from chatApp.models import RoomInfo, Anchor, ChatUser, ForkTrace,ForkRelation,CharacterCard
import json
import random
from chatApp.api.common.common import build_full_image_url

def parse_send_date(send_date_str):
    """解析 send_date 字符串为 datetime"""
    if not send_date_str:
        return None
    try:
        return datetime.strptime(send_date_str, "%B %d, %Y %I:%M%p")
    except Exception:
        return None


def safe_parse_json(data_raw):
    """安全解析 JSON"""
    if isinstance(data_raw, str):
        if not data_raw.strip():
            return {}
        try:
            return json.loads(data_raw)
        except json.JSONDecodeError:
            return {}
    return data_raw


@api_view(['GET'])
def get_latest_ai_rooms(request):
    """
    获取最新的 AI 消息（每个房间最新一条）
    GET /api/feed/get_latest_ai_rooms/?page=1&page_size=10
    支持按 uid 查询：?uid=xxx
    """
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))  # 默认每页 10 条
    offset = (page - 1) * page_size
    uid_filter = request.GET.get("uid", None)

    # MongoDB 连接
    client = MongoClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # 获取房间列表
    rooms_query = RoomInfo.objects.filter(is_show=0)  # 只展示 is_show=0
    if uid_filter:
        rooms_query = rooms_query.filter(uid=uid_filter)
    rooms = rooms_query.order_by('-updated_at')

    result = []

    for room in rooms:
        collection_name = room.room_id
        collection = db[collection_name]

        # 获取房间内最新 AI 消息
        latest_doc = collection.find_one({"data_type": "ai"}, sort=[("_id", -1)])
        if not latest_doc:
            continue

        # 安全解析 data
        data_dict = safe_parse_json(latest_doc.get("data", {}))

        filtered_data = {
            "name": data_dict.get("name"),
            "is_user": False,
            "send_date": data_dict.get("send_date"),
            "mes": data_dict.get("mes")
        }

        # 计算楼层（按插入顺序）
        chat_records = list(collection.find({}).sort("_id", 1))
        latest_floor = 0
        for index, item in enumerate(chat_records, start=1):
            if item.get("_id") == latest_doc.get("_id"):
                latest_floor = index
                break

        # 获取 username
        if room.file_branch == "main":
            try:
                user_obj = Anchor.objects.get(uid=room.uid)
                username = user_obj.username
                source_username = username  # main 分支源头就是它
            except Anchor.DoesNotExist:
                username = room.user_name or ""
                source_username = username
        else:
            try:
                user_obj = ChatUser.objects.get(id=room.uid)
                username = user_obj.username
            except ChatUser.DoesNotExist:
                username = room.user_name or ""

            # 查 fork 源头
            fork_trace = ForkTrace.objects.filter(current_room_id=room.room_id).first()
            if fork_trace:
                try:
                    source_anchor = Anchor.objects.get(uid=fork_trace.source_uid)
                    source_username = source_anchor.username
                except Anchor.DoesNotExist:
                    source_username = None
            else:
                source_username = None

        send_date_obj = parse_send_date(data_dict.get("send_date"))
        send_date_str = send_date_obj.strftime("%Y-%m-%d %H:%M:%S") if send_date_obj else None

        result.append({
            "room_id": room.room_id,
            "character_name": room.character_name,
            "title": room.title,
            "describe": room.describe,
            "username": username,
            "file_branch": room.file_branch,
            "source_username": source_username,
            "latest_message": filtered_data,
            "data_type": latest_doc.get("data_type"),
            "mes_html": latest_doc.get("mes_html", ""),
            "send_date": send_date_str,
            "floor": latest_floor
        })

    # 按发送时间降序
    result.sort(key=lambda x: x["send_date"] or "", reverse=True)

    # 分页
    total = len(result)
    paginated = result[offset: offset + page_size]

    return Response({
        "code": 0,
        "data": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "rooms": paginated
        }
    })


@api_view(['GET'])
def get_fork_relations(request):
    """
    获取 fork 关系，只返回 id 和 username
    GET /api/fork/relations/?page=1&page_size=10
    """
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))
    offset = (page - 1) * page_size

    fork_qs = ForkRelation.objects.all().order_by('-created_at')
    total = fork_qs.count()
    fork_list = fork_qs[offset: offset + page_size]

    result = []
    for fork in fork_list:
        # 发起者 username
        try:
            from_user = ChatUser.objects.get(id=fork.from_user_id)
            from_username = from_user.username
        except ChatUser.DoesNotExist:
            from_username = f"User {fork.from_user_id}"

        # 目标用户 username
        target_id = fork.target_id
        target_username = None
        if target_id.isdigit():  # 数字 id → 查 ChatUser
            try:
                target_user = ChatUser.objects.get(id=int(target_id))
                target_username = target_user.username
            except ChatUser.DoesNotExist:
                target_username = f"User {target_id}"
        else:  # 字符串 uid → 查 Anchor
            try:
                target_user = Anchor.objects.get(uid=target_id)
                target_username = target_user.username
            except Anchor.DoesNotExist:
                target_username = f"User {target_id}"

        result.append({
            "from_id": fork.from_user_id,
            "from_name": from_username,
            "target_id": fork.target_id,
            "target_name": target_username
        })

    return Response({
        "code": 0,
        "data": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "forks": result
        }
    })

@api_view(['GET'])
def random_fork_card(request):
    """
    随机返回 ForkRelation 中一条记录对应的 CharacterCard 的图片、角色名和用户名
    """
    # 1. 随机选一条 ForkRelation
    total_count = ForkRelation.objects.count()
    if total_count == 0:
        return Response({"success": False, "message": "ForkRelation 没有数据"}, status=404)

    random_index = random.randint(0, total_count - 1)
    fork = ForkRelation.objects.all()[random_index]

    # 2. 用 room_id 查 CharacterCard
    try:
        card = CharacterCard.objects.get(room_id=fork.room_id)
    except CharacterCard.DoesNotExist:
        return Response({"success": False, "message": "CharacterCard 未找到"}, status=404)

    # 3. 返回需要的字段
    data = {
        "target_id": fork.target_id,
        "username": card.username,
        "character_name": card.character_name,
        "image_path": build_full_image_url(request, card.image_path.url)

    }

    return Response({"success": True, "data": data})
