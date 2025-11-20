from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import RoomInfo, CharacterCard ,ForkRelation,Anchor ,ForkTrace,ChatUser
from chatApp.api.common.common import build_full_image_url,generate_new_room_id, generate_new_room_name
from pymongo import MongoClient
from django.conf import settings
from django.contrib.auth import get_user
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
import traceback
from django.utils import timezone
from django_redis import get_redis_connection  # 获取 Redis 连接
from rest_framework.pagination import PageNumberPagination

redis_client = get_redis_connection('default')  # 使用 django-redis 配置

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.get_database()

class ForkedListPagination(PageNumberPagination):
    page_size = 10  # 每页返回的条目数
    page_size_query_param = 'page_size'  # 可选的分页大小参数
    max_page_size = 100  # 最大页大小

#fork
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def fork_confirm(request):
    """
    Fork 确认接口
    """
    try:
        # ------------------ 获取当前登录用户 ------------------
        user = request.user
        if not user:
            return Response({"success": False, "message": "用户未登录"}, status=401)

        # 只获取 id 和 username
        user_id = user.id
        user_name = getattr(user, "username", "")

        # ------------------ 请求参数 ------------------
        target_id = request.data.get('target_id')
        room_id = request.data.get('room_id')
        floor = request.data.get('last_floor')

        if not all([target_id, room_id, floor]):
            return Response({"success": False, "message": "缺少必要参数"}, status=400)

        floor = int(floor)
        if floor < 1:
            return Response({"success": False, "message": "floor 必须 >= 1"}, status=400)

        # ------------------ 查询原房间 ------------------
        try:
            origin_room = RoomInfo.objects.get(room_id=room_id)
        except RoomInfo.DoesNotExist:
            return Response({"success": False, "message": "原房间不存在"}, status=404)

        # ------------------ 获取角色卡信息 ------------------
        character_card = CharacterCard.objects.filter(
            uid=origin_room.uid,
            character_name=origin_room.character_name
        ).first()
        character_name = character_card.character_name if character_card else "UnknownCharacter"
        is_private = int(character_card.is_private) if character_card else 0

        # ------------------ 生成新房间 name 和 id ------------------
        new_room_name = generate_new_room_name(origin_room.uid, character_name)
        new_room_id, character_date = generate_new_room_id(user_id, character_name)

        # ------------------ 创建新房间 ------------------
        new_room = RoomInfo.objects.create(
            uid=user_id,
            user_name=user_name,
            room_id=new_room_id,
            room_name=new_room_name,
            character_name=character_name,
            character_date=character_date,
            room_type=origin_room.room_type,
            file_name=origin_room.file_name,
            file_branch='branch',
            is_info=origin_room.is_info,
            is_show=is_private,
            created_at=timezone.now()
        )

        # ------------------ 写入 ForkRelation ------------------
        ForkRelation.objects.create(
            from_user_id=user_id,
            target_id=target_id,
            room_id=room_id,
            floor=floor,
            character_name=character_name,
            created_at=timezone.now()
        )

        # ------------------ 复制 MongoDB 聊天记录（≤ floor） ------------------
        client = MongoClient(settings.MONGO_URI)
        db = client[settings.MONGO_DB_NAME]

        origin_collection = db[str(room_id)]
        new_collection = db[str(new_room_id)]

        chat_records = list(origin_collection.find({}).sort("_id", 1))
        forked_chat_info = []

        for index, item in enumerate(chat_records, start=1):
            if index > floor:
                break
            new_item = item.copy()
            new_item.pop("_id", None)
            new_item.update({
                "uid": user_id,
                "username": user_name,
                "room_id": new_room_id,
                "room_name": new_room_name
            })
            new_collection.insert_one(new_item)

            data = new_item.get("data", {})
            forked_chat_info.append({
                "floor": index,
                "data_type": new_item.get("data_type"),
                "data": {
                    "name": data.get("name"),
                    "is_user": data.get("is_user"),
                    "send_date": data.get("send_date"),
                    "mes": data.get("mes")
                },
                "mes_html": new_item.get("mes_html", "")
            })

        # ------------------ 复制角色卡信息 ------------------
        try:
            origin_cards = CharacterCard.objects.filter(
                uid=origin_room.uid,
                character_name=origin_room.character_name
            )
            for card in origin_cards:
                CharacterCard.objects.create(
                    room_id=new_room_id,
                    uid=user_id,
                    username=user_name,
                    character_name=card.character_name,
                    image_name=card.image_name,
                    image_path=card.image_path,
                    character_data=card.character_data,
                    create_date=card.create_date,
                    language=card.language,
                    tags=card.tags,
                    is_private=card.is_private
                )
        except Exception as card_err:
            print("⚠️ 复制 CharacterCard 失败：", card_err)

        # ------------------ 写入 ForkTrace ------------------
        try:
            last_trace = ForkTrace.objects.filter(current_room_id=room_id).order_by('-created_at').first()
            if last_trace:
                source_room_id = last_trace.source_room_id
                source_uid = last_trace.source_uid
            else:
                source_room_id = origin_room.room_id
                source_uid = origin_room.uid

            ForkTrace.objects.create(
                source_room_id=source_room_id,
                source_uid=source_uid,
                prev_room_id=room_id,
                prev_uid=origin_room.uid,
                current_room_id=new_room_id,
                current_uid=user_id,
                created_at=timezone.now()
            )
        except Exception as trace_err:
            print("⚠️ 写入 ForkTrace 失败：", trace_err)

        # ------------------ 返回结果 ------------------
        return Response({
            "success": True,
            "message": "fork 成功",
            "data": {
                "room_info": {
                    "room_id": new_room.room_id
                }
            }
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "success": False,
            "message": f"fork 失败：{str(e)}"
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def forked_list(request):
    """
    获取当前用户已 fork 的新房间列表
    返回 fork_id、target_id，以及房间信息（room_id、room_name、title、describe、username）
    """
    user = request.user

    # 获取当前用户的所有 fork 记录
    forks = ForkTrace.objects.filter(current_uid=user.id).order_by('-created_at')

    # 使用分页器进行分页
    paginator = ForkedListPagination()
    result_page = paginator.paginate_queryset(forks, request)

    result_list = []
    for fork in result_page:
        try:

            # 获取当前新房间的 RoomInfo 信息
            room_info = RoomInfo.objects.get(room_id=fork.current_room_id)

            # 获取房间的图片信息
            image_info = build_full_image_url(request, room_info.uid, room_info.character_name)

            nickname_obj = ChatUser.objects.filter(id=room_info.uid).first()
            nickname = nickname_obj.nickname if nickname_obj and nickname_obj.nickname else ""

            # 构建返回的结果
            result_list.append({
                "room_id": room_info.room_id,
                "room_name": room_info.room_name,
                "uid": room_info.uid,
                "username": room_info.user_name,
                "nickname": nickname,
                "character_name": room_info.character_name,
                "character_date": room_info.character_date,
                "image_name": image_info['image_name'],
                "image_path": image_info['image_path'],
                "tags": image_info['tags'],
                "language": image_info['language'],
                "room_info": {
                    "title": room_info.title or "",
                    "describe": room_info.describe or "",
                    "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                    "room_type": room_info.room_type or 0,
                },
                "last_ai_reply_timestamp": room_info.last_ai_reply_timestamp
            })

        except RoomInfo.DoesNotExist:
            continue  # 如果房间信息不存在，跳过该项

    return Response({
        "code": 0,
        "message": "Success",
        "data": {
            "next": paginator.get_next_link(),  # 下一页的链接
            "previous": paginator.get_previous_link(),  # 上一页的链接
            "results": result_list  # 当前页面的房间列表
        }
    }, status=200)


@api_view(['GET'])
def anchor_forked_by(request):
    """
    查询指定主播被哪些用户 fork 过
    请求参数：
    - uid: 主播 UID（必填）

    返回：
    - fork_id
    - target_id
    - room信息：room_id、room_name、title、describe
    - 发起用户 username
    """
    uid = request.GET.get('uid')
    if not uid:
        return Response({"success": False, "message": "uid 必填"}, status=400)

    forks = ForkRelation.objects.filter(target_id=uid).order_by('-created_at')

    result_list = []
    for fork in forks:
        # 获取原房间信息
        try:
            room = RoomInfo.objects.get(room_id=fork.room_id)
        except RoomInfo.DoesNotExist:
            continue

        # 获取发起用户信息
        try:
            user = Anchor.objects.get(uid=fork.from_user_id)
            username = user.username
        except Anchor.DoesNotExist:
            username = "Unknown"

        result_list.append({
            "fork_id": fork.id,
            "target_id": fork.target_id,
            "room_id": room.room_id,
            "room_name": room.room_name,
            "title": room.title,
            "describe": room.describe,
            "username": username
        })

    return Response({
        "success": True,
        "data": result_list
    }, status=200)