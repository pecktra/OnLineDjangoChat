from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient
import json
import hashlib
from chatApp.models import RoomInfo, CharacterCard
from django_redis import get_redis_connection  # 获取 Redis 连接
from django.views.decorators.csrf import csrf_exempt
# 建立 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# 获取 Channel Layer
channel_layer = get_channel_layer()

# 创建 Redis 连接
redis_client = get_redis_connection('default')  # 使用 django-redis 配置

# 异步发送 WebSocket 消息
async def send_to_websocket(room_id, send_data):
    await channel_layer.group_send(
        "chat_" + room_id,
        {
            'type': 'chat_live_message',
            'data': send_data
        }
    )

# 包装为同步函数
sync_send_to_websocket = async_to_sync(send_to_websocket)

@csrf_exempt
@api_view(['POST'])
def chat_data(request):
    """
    聊天数据接口
    POST /api/chat/chat_data
    """
    username = request.data.get("username")
    uid = request.data.get("uid")
    character_name = request.data.get("character_name")
    character_date = request.data.get("character_date")
    data_str = request.data.get("data")  # 获取 data 字段
    mes_html = request.data.get("mes_html")
    isNewCreated = request.data.get("isNewCreated", None)

    # 确保必填参数存在
    if not all([username, uid, character_name, character_date, data_str]):
        return Response({"code": 1, "message": "缺少必填参数"}, status=400)

    try:
        # 处理 data_str
        if isinstance(data_str, str):
            try:
                data = json.loads(data_str)  # 解析 JSON 字符串
            except json.JSONDecodeError:
                return Response({"code": 1, "message": "数据格式错误，JSON 解码失败"}, status=400)
        elif isinstance(data_str, dict):
            data = data_str  # 直接使用字典
        else:
            return Response({"code": 1, "message": "数据格式错误，应该是字典或JSON字符串"}, status=400)

        # 确保 data 是字典
        if not isinstance(data, dict):
            return Response({"code": 1, "message": "数据格式错误，data 必须是字典"}, status=400)

        # 检查 mes 字段
        if data.get('mes', '') == '...':
            return Response({
                "code": 0,
                "message": "mes是...不接收"
            })

        # 判断数据类型
        if "chat_metadata" in data:
            data_type = "create"
        elif data.get("is_user") is True:
            data_type = "user"
        elif data.get("is_user") is False:
            data_type = "ai"
        else:
            data_type = "unknown"

        # 生成 room_id 和 room_name
        room_id = hashlib.sha1(f"{uid}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]
        room_name = f"{uid}_{character_name}_{character_date}"

        # MongoDB 插入数据（带楼层）
        collection = db[room_id]

        # ✅ 每条消息都是一层楼
        floor_count = collection.count_documents({}) + 1

        collection.insert_one({
            "username": username,
            "uid": uid,
            "character_name": character_name,
            "character_date": character_date,
            "room_id": room_id,
            "room_name": room_name,
            "data_type": data_type,
            "data": data,
            "mes_html": mes_html,
            "floor": floor_count  # ✅ 新增楼层字段
        })
        # # 准备转发数据
        # send_data = {
        #     'uid': uid,
        #     'username': username,
        #     'is_user': data.get('is_user', False),
        #     'sender_name': data.get('name') if data.get('is_user', False) else character_name,
        #     'send_date': data.get('send_date', ''),
        #     'live_message': data.get('mes', ''),
        #     'live_message_html': mes_html
        # }

        # 如果是创建房间，插入 MySQL
        if isNewCreated:
            if RoomInfo.objects.filter(room_id=room_id).exists():
                return Response({"code": 1, "message": "Room with the given uid and character_name already exists."},
                                status=400)

            file_name = request.data.get("file_name","0")
            file_branch = "main"
            if file_name and "Branch" in file_name:
                file_branch = "branch"




            # 创建房间记录
            room_info = RoomInfo(
                uid=uid,
                user_name=username,
                room_id=room_id,
                room_name=room_name,
                character_name=character_name,
                character_date=character_date,
                file_name=file_name,
                file_branch=file_branch,
                is_info=0,
                is_show=1  # 不公开 
            )
            room_info.save()

        # 转发 WebSocket 消息（取消注释以启用）
        # if send_data['live_message']:
        #     sync_send_to_websocket(room_id, send_data)

        return Response({
            "code": 0,
            "message": "操作成功，数据已处理并发送到 WebSocket"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({"code": 1, "message": f"服务器内部错误: {str(e)}"}, status=500)
