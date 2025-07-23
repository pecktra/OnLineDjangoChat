from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_redis import get_redis_connection  # 使用 django-redis 连接 Redis
from django.conf import settings
from pymongo import MongoClient

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.chat_db  # 连接到 chat_db 数据库

# 获取 Redis 连接
redis_client = get_redis_connection('default')  # 使用 django-redis 配置

@api_view(['GET'])
def get_live_status(request):
    """
    获取当前主播直播间状态列表
    GET /api/live/get_live_status?uid=<uid>&username=<username>
    """
    uid = request.GET.get("uid")
    username = request.GET.get("username")

    if not uid or not username:
        return Response({"code": 1, "message": "Missing uid or username"}, status=400)

    try:
        # 1. 获取 MongoDB 中所有集合名
        collections = db.list_collection_names()

        live_status_list = []

        # 2. 遍历所有集合
        for collection_name in collections:
            # 确保集合名中包含 uid
            if uid in collection_name:
                collection = db[collection_name]
                # 3. 查找当前集合中是否存在该 uid
                user = collection.find_one({"uid": uid})
                if user:
                    character_name = user.get("character_name")
                    if character_name:
                        # 4. 使用 Redis 查询该角色的直播状态
                        live_key = f"live_status:{uid}:{character_name}"
                        status_str = redis_client.get(live_key)

                        # 如果 Redis 中没有找到状态，则默认为正在直播
                        if status_str is None:
                            status = True  # 默认为直播中
                        else:
                            # 解码 Redis 中的字节数据并去除多余的空白字符
                            status_str = status_str.decode('utf-8').strip().lower()

                            # 判断状态，"start" 为 True, 其他为 False
                            status = True if status_str == "start" else False

                        live_status_list.append({
                            "uid": uid,
                            "character_name": character_name,
                            "status": status
                        })

        # 返回查询结果
        return Response({
            "code": 0,
            "data": {
                "live_status": live_status_list
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['POST'])
def change_live_status(request):
    """
    修改直播间直播状态
    POST /api/live/change_live_status
    """
    uid = request.data.get("uid")
    character_name = request.data.get("character_name")
    live_status = request.data.get("live_status")

    if not uid or not character_name or not live_status:
        return Response({"code": 1, "message": "Missing parameter(s)."}, status=400)

    if live_status not in ["start", "stop"]:
        return Response({"code": 1, "message": "Invalid live_status, must be 'start' or 'stop'."}, status=400)

    try:
        # 拼接 Redis 键
        key = f"live_status:{uid}:{character_name}"

        # 使用 Redis 原子操作设置直播状态
        redis_client.set(key, live_status)

        return Response({"code": 0, "message": "Live status updated successfully."})

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)
