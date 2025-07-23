from channels.layers import get_channel_layer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient
import json

# 建立 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# 获取 Channel Layer
channel_layer = get_channel_layer()

# 将 chat_data 改为异步函数
@api_view(['POST'])
async def chat_data(request):
    """
    聊天数据接口
    POST /api/chat/chat_data

    接收：
        - username
        - uid
        - chracter_name
        - data (json 字符串)

    存储：
        - room_id = uid + "_" + chracter_name
        - 每个 room_id 存一张 collection
    """
    username = request.data.get("username")
    uid = request.data.get("uid")
    character_name = request.data.get("chracter_name")
    data_str = request.data.get("data")

    if not username or not uid or not character_name or not data_str:
        return Response({"code": 1, "message": "Missing required parameter(s)."}, status=400)

    try:
        room_id = f"{uid}_{character_name}"

        # 解析 JSON
        data = json.loads(data_str)

        # 自动识别数据类型
        if "chat_metadata" in data:
            data_type = "create"
        elif data.get("is_user") is True:
            data_type = "user"
        elif data.get("is_user") is False:
            data_type = "ai"
        else:
            data_type = "unknown"

        # 每个 room_id 存一张 collection
        collection = db[room_id]

        # 将数据存入 MongoDB
        collection.insert_one({
            "username": username,
            "uid": uid,
            "character_name": character_name,
            "room_id": room_id,
            "data_type": data_type,
            "data": data
        })

        # 从 data 中获取需要转发的数据
        send_data = {
            'uid': uid,
            'username': username,
            'send_date': data.get('send_date', ''),
            'user_message': data.get('user_message', '')
        }

        # 将消息转发到 WebSocket
        if send_data['user_message']:
            # 使用 await 来异步发送消息
            await channel_layer.group_send(
                room_id,  # 这里传递的是 room_id，确保 WebSocket 消费者订阅该 room
                {
                    'type': 'chat_message',  # 指定要调用消费者中的 chat_message 方法
                    'data': send_data  # 发送的消息数据
                }
            )

        return Response({"code": 0})

    except json.JSONDecodeError as e:
        return Response({"code": 1, "message": f"JSON decode error: {str(e)}"}, status=400)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)
