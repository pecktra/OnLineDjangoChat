from django.http import JsonResponse
from chatApp.models import UserFollowedRoom,RoomInfo
from rest_framework.decorators import api_view
from django.contrib.auth import get_user
from django.core.paginator import Paginator
from rest_framework.response import Response
from django_redis import get_redis_connection


redis_client = get_redis_connection('default')

@api_view(['POST'])
def toggle_follow_room(request):
    """
    用户关注或取消关注直播间接口
    POST /api/live/toggle_follow_room
    """
    try:
        user_id = request.data.get('user_id')  # 用户ID
        room_id = request.data.get('room_id')  # 直播间ID
        room_name = request.data.get('room_name')  # 直播间名称

        # 查找用户关注的该直播间记录
        followed_room, created = UserFollowedRoom.objects.get_or_create(
            user_id=user_id,room_id=room_id, room_name=room_name,
            defaults={'status': 1}  # 默认关注状态为 1 (关注)
        )

        # 如果用户已关注，取消关注：将 status 设置为 0
        if followed_room.status == 1:
            followed_room.status = 0
            followed_room.save()
            return JsonResponse({
                "code": 0,
                "message": "Unfollowed the room successfully",
                "data": {
                    "user_id": user_id,
                    "room_id": room_id,
                    "room_name": room_name,
                    "status": False  # false 表示取消关注
                }
            })

        # 如果用户未关注，进行关注：将 status 设置为 1
        elif followed_room.status == 0:
            followed_room.status = 1
            followed_room.save()
            return JsonResponse({
                "code": 0,
                "message": "Followed the room successfully",
                "data": {
                    "user_id": user_id,
                    "room_id": room_id,
                    "room_name": room_name,
                    "status": True  # true 表示已关注
                }
            })

        # 如果数据库插入失败
        return JsonResponse({"code": 1, "message": "Operation failed"}, status=400)

    except Exception as e:
        return JsonResponse({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['GET'])
def get_followed_rooms(request):
    """
    获取用户关注的所有直播间列表（不带分页）
    GET /api/live/get_followed_rooms
    """
    try:
        user = get_user(request)  # 获取当前用户

        if not user:
            return JsonResponse({"code": 1, "message": "User not authenticated"}, status=400)
        live_status_list = []
        # 获取所有关注状态为1的直播间
        followed_rooms = UserFollowedRoom.objects.filter(user_id=user.id, status=1)
        if followed_rooms:
            follow_room_ids = [row.room_id for row in followed_rooms]
            room_infos = RoomInfo.objects.filter(room_id__in=follow_room_ids)

            # 组织结果

            if room_infos:
                for room_info in room_infos:
                    is_status = redis_client.get(room_info.room_id)
                    if is_status:
                        live_status_list.append({
                            "room_id": room_info.room_id,
                            "room_name": room_info.room_name,
                            "uid": room_info.uid,
                            "username": room_info.user_name,
                            "live_num": 0,
                            "character_name": room_info.character_name,
                            "character_date": room_info.character_date,
                            "room_info": {
                                    "title": room_info.title if room_info.title is not None and room_info.title != "" else "",
                                    "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                                    "room_type": room_info.room_type if room_info.room_type is not None and room_info.room_type != "" else 0
                                }
                        })
        return Response({
            "code": 0,
            "data": {"lives_info": live_status_list}
        })



    except Exception as e:
        return JsonResponse({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)