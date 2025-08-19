from django.http import JsonResponse
from chatApp.models import UserFollowedRoom
from rest_framework.decorators import api_view

@api_view(['POST'])
def toggle_follow_room(request):
    """
    用户关注或取消关注直播间接口
    POST /api/live/toggle_follow_room
    """
    try:
        user_id = request.data.get('user_id')  # 用户ID
        room_name = request.data.get('room_name')  # 直播间ID

        # 查找用户关注的该直播间记录
        followed_room, created = UserFollowedRoom.objects.get_or_create(
            user_id=user_id, room_name=room_name,
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
                    "room_name": room_name,
                    "status": True  # true 表示已关注
                }
            })

        # 如果数据库插入失败
        return JsonResponse({"code": 1, "message": "Operation failed"}, status=400)

    except Exception as e:
        return JsonResponse({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)
