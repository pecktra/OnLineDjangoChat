from rest_framework.decorators import api_view
from rest_framework.response import Response
from pymongo import MongoClient
from django.conf import settings
import traceback

# ✅ 统一初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]


@api_view(['GET'])
def get_room_chat(request):
    """
    获取指定房间的聊天记录（支持增量拉取）
    GET /api/chat/get_room_chat?room_id=<room_id>&last_floor=<last_floor>

    参数：
    - room_id: 房间ID，必填
    - last_floor: 上次拉取的最后一楼（默认0，表示全量）
    """
    room_id = request.GET.get("room_id")
    if not room_id:
        return Response({"code": 1, "message": "Missing room_id parameter"}, status=400)

    # 默认从 0 楼开始（即全量拉取）
    try:
        last_floor = int(request.GET.get("last_floor", 0))
    except ValueError:
        return Response({"code": 1, "message": "Invalid last_floor parameter"}, status=400)

    try:
        collection = db[room_id]
        chat_records = list(collection.find({}).sort("_id", 1))  # 按时间排序

        result = []
        for index, item in enumerate(chat_records, start=1):
            # ✅ 跳过 <= last_floor 的记录，只取比它新的
            if index <= last_floor:
                continue

            data = item.get("data", {})
            filtered_data = {
                "name": data.get("name"),
                "is_user": data.get("is_user"),
                "send_date": data.get("send_date"),
                "mes": data.get("mes")
            }

            result.append({
                "floor": index,
                "data_type": item.get("data_type"),
                "data": filtered_data,  # ✅ 精简后的 data
                "mes_html": item.get("mes_html", "")
            })

        return Response({
            "code": 0,
            "message": "success",
            "data": result
        }, status=200)

    except Exception as e:
        print(traceback.format_exc())
        return Response({"code": 2, "message": str(e)}, status=500)
