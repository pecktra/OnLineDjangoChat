from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient
import json


# 建立 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]


@api_view(['POST'])
def chat_data(request):
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

        collection.insert_one({
            "username": username,
            "uid": uid,
            "character_name": character_name,
            "room_id": room_id,
            "data_type": data_type,
            "data": data
        })

        return Response({"code": 0})

    except json.JSONDecodeError as e:
        return Response({"code": 1, "message": f"JSON decode error: {str(e)}"}, status=400)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)
