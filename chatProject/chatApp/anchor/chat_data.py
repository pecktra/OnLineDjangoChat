from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient
import json
import hashlib
from django_redis import get_redis_connection  # 获取 Redis 连接

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

@api_view(['POST'])
def chat_data(request):
    """
    聊天数据接口
    POST /api/chat/chat_data
    """
    username = request.data.get("username")
    uid = request.data.get("uid")
    character_name = request.data.get("character_name")
    data_str = request.data.get("data")  # 获取 data 字段





    # 确保传递的参数都存在
    if not username or not uid or not character_name or not data_str:
        return Response({"code": 1, "message": "缺少必填参数"}, status=400)

    try:
        # 如果 data_str 是字符串，尝试将其转换为字典
        if isinstance(data_str, str):
            try:
                data = json.loads(data_str)  # 解析 JSON 字符串
            except json.JSONDecodeError:
                return Response({"code": 1, "message": "数据格式错误，JSON 解码失败"}, status=400)
        elif isinstance(data_str, dict):
            data = data_str  # 直接使用字典
        else:
            return Response({"code": 1, "message": "数据格式错误，应该是字典或JSON字符串"}, status=400)


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
        room_id = hashlib.md5(f"{uid}_{character_name}".encode('utf-8')).hexdigest()
        room_name = f"{uid}_{character_name}"

        # 检查 Redis 是否已经有该 room_name
        live_key = f"live_status:{uid}:{character_name}"
        if not redis_client.exists(live_key):
            redis_client.set(live_key, "stop")  # 默认设置为 'stop'，表示直播未开始

        # MongoDB 插入数据
        collection = db[room_name]
        collection.insert_one({
            "username": username,
            "uid": uid,
            "character_name": character_name,
            "room_id": room_id,
            "room_name": room_name,
            "data_type": data_type,
            "data": data
        })

        # 准备转发数据
        send_data = {
            'uid': uid,
            'username': username,
            'is_user': data.get('is_user', False),
            'sender_name': data.get('name') if data.get('is_user', False) else character_name,
            'send_date': data.get('send_date', ''),
            'live_message': data.get('mes', '')
        }


        # 转发 WebSocket 消息
        print("11111111111111")
        print(send_data['live_message'])
        print(room_id)
        if send_data['live_message']:
            sync_send_to_websocket(room_id, send_data)

        return Response({
            "code": 0,
            "message": "操作成功，数据已处理并发送到 WebSocket"
        })

    except Exception as e:
        return Response({"code": 1, "message": f"服务器内部错误: {str(e)}"}, status=500)