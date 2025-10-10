from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import RoomInfo, CharacterCard ,ForkRelation
from common.utils import build_full_image_url
from pymongo import MongoClient
from django.conf import settings
from django.contrib.auth import get_user

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.get_database()

#预览
@api_view(['GET'])
def fork_preview(request):
    """
    Fork 预览接口：
    查询被 fork 的房间信息及聊天记录（已 fork 楼层 <= last_floor）

    请求参数：
    - target_id: 被 fork 对象ID（用户id 或 主播uid）【必填】
    - room_id: 要 fork 的房间ID【必填】
    - last_floor: 已 fork 的最后楼层【必填，整数 >=1】

    返回：
    {
        "code": 0,
        "success": true,
        "message": "获取成功",
        "data": {
            "room_info": {...},
            "chat_info": [...]
        }
    }
    """
    target_id = request.GET.get('target_id')
    room_id = request.GET.get('room_id')
    last_floor_str = request.GET.get('last_floor')

    # 参数检查
    if not target_id or not room_id or last_floor_str is None:
        return Response({
            "code": 1,
            "success": False,
            "message": "target_id, room_id 和 last_floor 都必须提供"
        }, status=400)

    # 验证 last_floor
    try:
        last_floor = int(last_floor_str)
        if last_floor < 1:
            return Response({
                "code": 1,
                "success": False,
                "message": "last_floor 必须 >= 1"
            }, status=400)
    except ValueError:
        return Response({
            "code": 1,
            "success": False,
            "message": "last_floor 必须是整数"
        }, status=400)

    # 查询房间信息
    try:
        room = RoomInfo.objects.get(room_id=room_id)
    except RoomInfo.DoesNotExist:
        return Response({
            "code": 1,
            "success": False,
            "message": "房间不存在"
        }, status=404)

    # 查询角色卡信息
    character_info = {}
    try:
        character_card = CharacterCard.objects.filter(room_id=room.room_id).first()
        if character_card:
            image_path = build_full_image_url(request, character_card.image_path.url)
            character_info = {
                "character_name": character_card.character_name,
                "image_name": character_card.image_name,
                "image_path": image_path
            }
    except Exception:
        character_info = {}

    # 查询 MongoDB 聊天记录
    chat_info = []
    try:
        collection = db[room.room_id]
        chat_records = list(collection.find({}).sort("_id", 1))

        for index, item in enumerate(chat_records, start=1):
            if index > last_floor:
                break

            data = item.get("data", {})
            filtered_data = {
                "name": data.get("name"),
                "is_user": data.get("is_user"),
                "send_date": data.get("send_date"),
                "mes": data.get("mes")
            }

            chat_info.append({
                "floor": index,
                "data_type": item.get("data_type"),
                "data": filtered_data,
                "mes_html": item.get("mes_html", "")
            })
    except Exception as e:
        return Response({
            "code": 1,
            "success": False,
            "message": f"获取聊天历史失败: {str(e)}"
        }, status=500)

    # 返回结果
    return Response({
        "code": 0,
        "success": True,
        "message": "获取成功",
        "data": {
            "room_info": {
                "uid": room.uid,
                "user_name": room.user_name,
                "room_id": room.room_id,
                "room_name": room.room_name,
                "title": room.title,
                "describe": room.describe,
                **character_info
            },
            "chat_info": chat_info
        }
    })


#fork
@api_view(['POST'])
def fork_confirm(request):
    """
    Fork 确认接口：
    - 创建 fork 关系记录
    - 生成新的房间（room_id 按 sha1 加密规则生成）
    - 从 MongoDB 复制聊天记录（≤ floor）
    - 新房间继承角色卡信息，不新建
    - 前端可自定义 title、describe
    - 返回新房间信息 + 已 fork 的聊天记录
    """
    try:
        # 请求参数
        from_user_id = request.data.get('from_user_id')  # 发起 fork 的用户
        room_id = request.data.get('room_id')            # 被 fork 房间ID
        floor = request.data.get('floor')                # fork 楼层
        title = request.data.get('title', '')            # 新房间标题
        describe = request.data.get('describe', '')      # 新房间描述

        # 参数校验
        if not all([from_user_id, room_id, floor]):
            return Response({"success": False, "message": "缺少必要参数"}, status=400)

        floor = int(floor)
        if floor < 1:
            return Response({"success": False, "message": "floor 必须 >= 1"}, status=400)

        # 获取当前用户
        user = get_user(request)
        if not user:
            return Response({"success": False, "message": "用户未登录"}, status=401)

        # 查询原房间
        try:
            origin_room = RoomInfo.objects.get(room_id=room_id)
        except RoomInfo.DoesNotExist:
            return Response({"success": False, "message": "原房间不存在"}, status=404)

        # 获取角色卡信息
        character_card = CharacterCard.objects.filter(room_id=room_id).first()
        character_name = character_card.character_name if character_card else "UnknownCharacter"
        is_private = int(character_card.is_private) if character_card else 0

        # 生成新房间名
        timestamp_str = timezone.now().strftime("%Y-%m-%d @%Hh %Mm %Ss %fms")
        new_room_name = f"Branch_{origin_room.room_name}_{character_name}_{timestamp_str}"

        # 生成新的 room_id
        character_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        new_room_id = hashlib.sha1(f"Branch_{user.id}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]

        # 创建新房间
        new_room = RoomInfo.objects.create(
            uid=user.id,                 # 新房间属于当前用户
            user_name=user.username,
            room_id=new_room_id,
            room_name=new_room_name,
            character_name=character_name,
            character_date=character_date,
            title=title,
            describe=describe,
            room_type=origin_room.room_type,
            file_name=file_name,
            file_branch=file_branch,
            is_show=is_private,          # 与角色卡 is_private 保持一致
            created_at=timezone.now()
        )

        # === 写入 ForkRelation，target_id 为新房间 uid ===
        ForkRelation.objects.create(
            from_user_id=from_user_id,
            target_id=new_room.uid,      # 新房间所属用户ID
            room_id=room_id,             # 原房间ID
            floor=floor,
            created_at=timezone.now()
        )

        # 复制 MongoDB 聊天记录（≤ floor）
        origin_collection = db[str(room_id)]
        new_collection = db[str(new_room_id)]
        chat_records = list(origin_collection.find({}).sort("_id", 1))
        forked_chat_info = []  # 返回给前端的聊天记录
        for index, item in enumerate(chat_records, start=1):
            if index > floor:
                break
            # 插入到新房间 MongoDB
            new_collection.insert_one(item)
            # 构造返回数据
            data = item.get("data", {})
            forked_chat_info.append({
                "floor": index,
                "data_type": item.get("data_type"),
                "data": {
                    "name": data.get("name"),
                    "is_user": data.get("is_user"),
                    "send_date": data.get("send_date"),
                    "mes": data.get("mes")
                },
                "mes_html": item.get("mes_html", "")
            })

        # 返回结果
        return Response({
            "success": True,
            "message": "fork 成功",
            "data": {
                "room_info": {
                    "room_id": new_room.room_id,
                    "room_name": new_room.room_name,
                    "title": new_room.title,
                    "describe": new_room.describe,
                    "uid": new_room.uid,
                    "user_name": new_room.user_name,
                },
                "chat_info": forked_chat_info
            }
        }, status=200)

    except Exception as e:
        traceback.print_exc()
        return Response({
            "success": False,
            "message": f"fork 失败：{str(e)}"
        }, status=500)


@api_view(['GET'])
def forked_list(request):
    """
    获取当前用户已 fork 的房间列表
    返回 fork_id、target_id，以及房间信息（room_id、room_name、title、describe、username）
    """
    user = get_user(request)
    if not user:
        return Response({"success": False, "message": "用户未登录"}, status=401)

    forks = ForkRelation.objects.filter(from_user_id=user.id).order_by('-created_at')

    result_list = []
    for fork in forks:
        # 获取原房间信息
        try:
            room = RoomInfo.objects.get(room_id=fork.room_id)
        except RoomInfo.DoesNotExist:
            continue

        result_list.append({
            "fork_id": fork.id,
            "target_id": fork.target_id,
            "room_id": room.room_id,
            "room_name": room.room_name,
            "title": room.title,
            "describe": room.describe,
            "username": room.user_name
        })

    return Response({
        "success": True,
        "data": result_list
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