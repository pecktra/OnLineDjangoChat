from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import RoomInfo, CharacterCard
from common.utils import build_full_image_url
from pymongo import MongoClient
from django.conf import settings

# 初始化 MongoDB 连接（假设你在 settings 里配置了 MONGO_URI）
client = MongoClient(settings.MONGO_URI)
db = client.get_database()

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
    - room_info: 房间信息 + 角色卡信息
    - chat_info: 已 fork 的聊天记录列表，每条包含 floor、data_type、data、mes_html
    """
    # 1. 获取请求参数
    target_id = request.GET.get('target_id')
    room_id = request.GET.get('room_id')
    last_floor_str = request.GET.get('last_floor')

    if not target_id or not room_id or last_floor_str is None:
        return Response({"success": False, "message": "target_id, room_id 和 last_floor 都必须提供"}, status=400)

    # 2. 验证 last_floor
    try:
        last_floor = int(last_floor_str)
        if last_floor < 1:
            return Response({"success": False, "message": "last_floor 必须 >= 1"}, status=400)
    except ValueError:
        return Response({"success": False, "message": "last_floor 必须是整数"}, status=400)

    # 3. 查询房间信息
    try:
        room = RoomInfo.objects.get(room_id=room_id)
    except RoomInfo.DoesNotExist:
        return Response({"success": False, "message": "房间不存在"}, status=404)

    # 4. 查询角色卡信息
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

    # 5. 查询 MongoDB 聊天记录（楼层 <= last_floor）
    chat_info = []
    try:
        collection = db[room.room_id]
        chat_records = list(collection.find({}).sort("_id", 1))  # 按时间排序

        for index, item in enumerate(chat_records, start=1):
            # 只取 <= last_floor 的楼层
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
        return Response({"success": False, "message": f"获取聊天历史失败: {str(e)}"}, status=500)

    # 6. 返回结果
    data = {
        "success": True,
        "room_info": {
            "uid": room.uid,
            "user_name": room.user_name,
            "room_id": room.room_id,
            "room_name": room.room_name,
            "title": room.title,
            "describe": room.describe,
            **character_info  # 合并角色卡信息
        },
        "chat_info": chat_info
    }

    return Response(data)
