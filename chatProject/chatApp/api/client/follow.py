from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse
from chatApp.models import UserFollowRelation, ChatUser
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # 确保用户已认证
def toggle_follow_user(request):
    """
    用户关注或取消关注另一个用户
    POST /api/user/toggle_follow_user
    """
    try:
        follower_id = request.user.id  # 使用 JWT 认证后的用户ID
        followed_id = request.data.get('followed_id')  # 被关注的用户ID

        if not followed_id:
            return JsonResponse({"code": 1, "message": "Missing followed_id"}, status=400)

        # 查找关注关系
        relation, created = UserFollowRelation.objects.get_or_create(
            follower_id=follower_id,
            followed_id=followed_id,
            defaults={'status': True}
        )

        # 如果已关注，则取消关注
        if relation.status:
            relation.status = False
            relation.save()
            return JsonResponse({
                "code": 0,
                "message": "Unfollowed successfully",
                "data": {
                    "followed_id": followed_id,
                    "status": False
                }
            })

        # 如果未关注，则重新关注
        else:
            relation.status = True
            relation.save()
            return JsonResponse({
                "code": 0,
                "message": "Followed successfully",
                "data": {
                    "followed_id": followed_id,
                    "status": True
                }
            })

    except Exception as e:
        return JsonResponse({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])  # 确保用户已认证
def get_followed_users(request):
    """
    获取当前用户关注的所有用户
    GET /api/user/get_followed_users
    """
    try:
        user_id = request.user.id  # 使用 JWT 认证后的用户ID

        # 查找当前用户关注的所有人
        followed_relations = UserFollowRelation.objects.filter(follower_id=user_id, status=True)

        followed_list = []
        for r in followed_relations:
            followed_user = ChatUser.objects.get(id=r.followed_id)

            # 如果 nickname 为空，则使用 username
            nickname = followed_user.nickname if followed_user.nickname else None  # 返回 None 或空字符串

            followed_list.append({
                "followed_id": r.followed_id,
                "nickname": nickname,
                "username": followed_user.username,
                "followed_at": r.followed_at
            })

        return Response({
            "code": 0,
            "data": {
                "followed_users": followed_list
            }
        })

    except Exception as e:
        return JsonResponse({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)