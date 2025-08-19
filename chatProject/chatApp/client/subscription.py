from django_redis import get_redis_connection
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation
import json
from chatApp.models import Subscription, UserBalance, Anchor, AnchorBalance, ChatUser
from django.core.cache import cache

# 用户订阅主播接口
@api_view(['POST'])
def subscribe_to_anchor(request):
    """
    用户订阅主播接口，扣除用户的钻石余额，订阅时间为一个月
    POST /api/subscribe/subscribe_to_anchor
    """
    try:
        # 获取请求数据
        user_id = request.data.get('user_id')  # 用户ID
        anchor_uid = request.data.get('anchor_id')  # 主播uid
        diamonds_to_pay = request.data.get('amount')  # 支付的钻石数量

        # 检查 diamonds_to_pay 是否为 None 或无效
        if diamonds_to_pay is None:
            return JsonResponse({"code": 1, "message": "Amount of diamonds to pay is required."}, status=400)

        try:
            diamonds_to_pay = Decimal(diamonds_to_pay)  # 转换为 Decimal 类型
        except (ValueError, InvalidOperation):
            return JsonResponse({"code": 1, "message": "Invalid diamonds to pay."}, status=400)

        # 查找用户和用户余额对象
        user = get_object_or_404(ChatUser, id=user_id)
        user_balance = get_object_or_404(UserBalance, user_id=user.id)

        # 查找主播，使用 uid 进行查找
        anchor = get_object_or_404(Anchor, uid=anchor_uid)

        # 查找主播的余额记录
        anchor_balance = get_object_or_404(AnchorBalance, anchor_id=anchor.uid)

        # 检查余额是否足够
        if user_balance.balance is None or user_balance.balance < diamonds_to_pay:
            return JsonResponse({"code": 1, "message": "Insufficient balance."}, status=400)

        # 获取 Redis 连接
        redis_client = get_redis_connection('subscribe')

        # Redis key：使用用户ID和主播UID作为键
        redis_key = f"subscription:{user.id}:{anchor.uid}"

        # 检查 Redis 中是否存在有效的订阅信息
        redis_data = redis_client.get(redis_key)

        if redis_data:
            # 如果 Redis 中有订阅记录，说明订阅尚未过期
            return JsonResponse({"code": 1, "message": "You have already subscribed to this anchor and the subscription is still active."}, status=400)

        # 开始数据库事务，确保数据一致性
        with transaction.atomic():
            # 更新主播余额和总打赏金额
            anchor_balance.balance += diamonds_to_pay  # 增加主播当前余额
            anchor_balance.total_donations += diamonds_to_pay  # 增加主播的总打赏金额
            anchor_balance.save()

            # 扣除用户余额
            if not user_balance.deduct_balance(diamonds_to_pay):
                return JsonResponse({"code": 1, "message": "Failed to deduct balance"}, status=500)

            # 创建订阅记录（不再记录状态，只有历史数据）
            subscription = Subscription(
                user=user,
                anchor=anchor,
                diamonds_paid=diamonds_to_pay,
                subscription_date=timezone.now()  # 订阅时间
            )
            subscription.save()

            # 计算过期时间
            expiry_date = timezone.now() + timedelta(days=30)
            expiry_date_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S')  # 格式化过期时间

            # 将订阅信息存储到 Redis 中，设置过期时间为 30 天
            redis_data = {
                "user_id": user.id,
                "anchor_id": anchor.uid,
                "diamonds_paid": float(diamonds_to_pay),
                "subscription_date": timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                "expiry_date": expiry_date_str  # 存储格式化后的过期时间
            }

            redis_client.set(redis_key, json.dumps(redis_data), ex=30 * 24 * 60 * 60)

        # 返回成功响应
        return JsonResponse({
            "code": 0,
            "message": "Subscription successful",
            "data": {
                "user_id": user.id,
                "anchor_id": anchor.uid,
                "subscription_date": subscription.subscription_date.strftime('%Y-%m-%d %H:%M:%S'),
                "diamonds_paid": float(diamonds_to_pay),
                "expiry_date": expiry_date_str
            }
        })

    except Exception as e:
        # 处理异常并返回 500 错误
        return JsonResponse({
            "code": 1,
            "message": f"Internal server error: {str(e)}"
        }, status=500)

# 获取用户的所有有效订阅记录接口
@api_view(['GET'])
def get_subscriptions(request):
    """
    获取用户的所有有效订阅记录（只返回未过期的订阅）
    GET /api/subscribe/get_subscriptions?user_id=1
    """
    try:
        # 获取请求中的用户ID
        user_id = request.GET.get('user_id')

        if not user_id:
            return JsonResponse({"code": 1, "message": "Missing user_id parameter"}, status=400)

        # 构建Redis的前缀 key
        redis_key_prefix = f"subscription:{user_id}:"

        # 获取该用户所有订阅的 Redis key
        redis_client = get_redis_connection('subscribe')  # 使用 'subscribe' 配置连接到第二个数据库
        subscription_keys = redis_client.keys(f"{redis_key_prefix}*")  # 获取以 user_id 为前缀的所有订阅 key

        if not subscription_keys:
            return JsonResponse({"code": 1, "message": "No subscriptions found for this user"}, status=404)

        # 构建返回的订阅列表数据
        subscription_list = []
        for redis_key in subscription_keys:
            # 获取订阅数据
            redis_data = redis_client.get(redis_key)

            if redis_data:
                redis_data = json.loads(redis_data)

                # 获取 diamonds_paid，确保它是 float 类型
                diamonds_paid = float(redis_data.get("diamonds_paid", 0))

                # 获取 expiry_date，确保它是字符串，转换为时间戳比较
                expiry_date_str = redis_data.get("expiry_date")
                if expiry_date_str:
                    expiry_date_timestamp = timezone.make_aware(timezone.datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S')).timestamp()

                    # 过滤掉过期的订阅
                    if expiry_date_timestamp > timezone.now().timestamp():
                        subscription_list.append({
                            "anchor_id": redis_data.get("anchor_id"),
                            "diamonds_paid": diamonds_paid,
                            "subscription_date": redis_data.get("subscription_date"),
                            "subscription_end_date": expiry_date_str,  # 返回原始的到期日期字符串
                        })

        if not subscription_list:
            return JsonResponse({"code": 1, "message": "No active subscriptions found for this user"}, status=404)

        return JsonResponse({
            "code": 0,
            "message": "Active subscriptions retrieved successfully",
            "data": {
                "subscriptions": subscription_list
            }
        })

    except Exception as e:
        # 处理异常并返回 500 错误
        return JsonResponse({
            "code": 1,
            "message": f"Internal server error: {str(e)}"
        }, status=500)

