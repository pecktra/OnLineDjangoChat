from rest_framework.pagination import CursorPagination
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from chatApp.models import CharacterCard, Favorite, RoomInfo
from chatApp.api.common.common import build_full_image_url
from rest_framework.pagination import PageNumberPagination

class ChatHistoryPagination(PageNumberPagination):
    page_size = 10  # 设置每页显示的条数
    page_size_query_param = 'page_size'
    max_page_size = 100  # 设置最大页数

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 确保用户已认证
def favorite_list(request):
    """
    获取当前用户的收藏列表（仅返回 status=1 的收藏）
    使用 JWT 解密获取当前用户的 UID
    """
    # 获取当前用户的 UID
    uid = request.user.id  # 假设 UID 存储在 User 模型的 id 字段

    favorites = Favorite.objects.filter(uid=uid, status=1)

    # 使用分页器对结果进行分页
    paginator = ChatHistoryPagination()
    result_page = paginator.paginate_queryset(favorites, request)

    data = []
    for fav in result_page:
        try:
            # 获取 RoomInfo 信息
            room_info = RoomInfo.objects.get(room_id=fav.room_id)

            image_info = build_full_image_url(request, uid=room_info.uid, room_id=room_info.room_id)
            # 构建返回数据
            data.append({
                "room_id": room_info.room_id,
                "room_name": room_info.room_name,
                "uid": room_info.uid,
                "username": room_info.user_name,
                "character_name": room_info.character_name,
                "character_date": room_info.character_date,
                "image_name": image_info['image_name'],
                "image_path": image_info['image_path'],
                "tags": image_info['tags'],
                "language": image_info['language'],
                "room_info": {
                    "title": room_info.title or "",
                    "describe": room_info.describe or "",
                    "coin_num": room_info.coin_num if room_info.coin_num is not None else 0,
                    "room_type": room_info.room_type or 0,
                },
                "last_ai_reply_timestamp": room_info.last_ai_reply_timestamp,
                "collected_at": fav.created_at,
            })
        except (RoomInfo.DoesNotExist):
            continue

    # 返回分页后的响应
    return Response({
        "code": 0,
        "message": "Success",
        "data": {
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": data
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 确保用户已认证
def favorite_card(request):
    """
    用户收藏或取消收藏角色卡（uid + room_id）
    action = 1 表示收藏，action = 0 表示取消收藏
    """
    # 获取当前用户的 UID
    uid = request.user.id  # 假设 UID 存储在 User 模型的 id 字段
    room_id = request.data.get("room_id")  # 卡片 room_id
    action = request.data.get("action")  # 1 或 0

    if not uid or not room_id:
        return Response({"success": False, "message": "uid 和 room_id 必填"}, status=400)

    if action not in [0, 1, "0", "1"]:
        return Response({"success": False, "message": "action 参数错误，必须是 0 或 1"}, status=400)

    try:
        card = RoomInfo.objects.get(room_id=room_id)
    except CharacterCard.DoesNotExist:
        return Response({"success": False, "message": "房间不存在"}, status=404)

    # 获取或创建收藏记录
    fav, created = Favorite.objects.get_or_create(uid=uid, room_id=room_id)

    # 更新收藏状态
    fav.status = int(action)
    fav.save(update_fields=["status", "updated_at"])

    if int(action) == 1:
        return Response({"success": True, "message": "收藏成功"})
    else:
        return Response({"success": True, "message": "取消收藏成功"})


