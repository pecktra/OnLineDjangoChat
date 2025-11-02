from django_redis import get_redis_connection
from django.http import JsonResponse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from decimal import Decimal, InvalidOperation
import json
from chatApp.models import  UserBalance, Anchor, AnchorBalance, ChatUser,RoomInfo, PaymentExpenditureRecord
from django.core.cache import cache
from django.contrib.auth import get_user
from rest_framework.response import Response
# 用户订阅主播接口
@api_view(['POST'])
def subscribe_to_anchor(request):
    """
    用户订阅主播接口，扣除用户余额，订阅时间为一个月
    POST /api/subscribe/subscribe_to_anchor
    """
    try:
        user_id = request.data.get('user_id')
        anchor_uid = request.data.get('anchor_id')
        amount = request.data.get('amount')  # 支付金额（余额）

        if not user_id or not anchor_uid or amount is None:
            return JsonResponse({"code": 1, "message": "Missing required parameters."}, status=400)

        try:
            amount = Decimal(amount)
        except Exception:
            return JsonResponse({"code": 1, "message": "Invalid amount format."}, status=400)

        # 改动点：允许 amount = 0
        if amount < 0:
            return JsonResponse({"code": 1, "message": "Amount must be greater than or equal to 0."}, status=400)

        # 获取用户和余额
        user = ChatUser.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({"code": 1, "message": "User not found."}, status=404)

#         user_balance = UserBalance.objects.filter(user_id=user_id).first()
#         if not user_balance:
#             return JsonResponse({"code": 1, "message": "User balance not found."}, status=404)

#         if user_balance.balance < amount:
#             return JsonResponse({"code": 1, "message": "Insufficient balance."}, status=400)

        # 获取主播
        anchor = Anchor.objects.filter(uid=anchor_uid).first()
        if not anchor:
            return JsonResponse({"code": 1, "message": "Anchor not found."}, status=404)

        # 获取或创建主播余额
#         anchor_balance, _ = AnchorBalance.objects.get_or_create(
#             anchor_id=anchor.uid,
#             defaults={'balance': Decimal('0.00'), 'total_received': Decimal('0.00')}
#         )

        # 计算 crypto_amount（1:5）
#         crypto_amount = amount / Decimal('5')

        # Redis key
        redis_client = get_redis_connection('subscribe')
        redis_key = f"subscription:{user.id}:{anchor.uid}"
        if redis_client.get(redis_key):
            return JsonResponse({
                "code": 1,
                "message": "You have already subscribed to this anchor and the subscription is still active."
            }, status=400)

        with transaction.atomic():
            # 暂时不用扣费逻辑
#             user_balance.balance -= amount
#             user_balance.save()

            # 暂时不用主播余额逻辑
#             anchor_balance.balance += amount
#             anchor_balance.total_received += amount
#             anchor_balance.save()

            # 暂时不用支出记录
#             expenditure_record = PaymentExpenditureRecord.objects.create(
#                 user_id=user.id,
#                 anchor_id=anchor.uid,
#                 payment_type='subscription',
#                 payment_source='subscription',
#                 amount=amount,
#                 currency='ZS',
#             )

            # 保存订阅信息到 Redis（过期30天）
            subscription_date = timezone.now()
            expiry_date = subscription_date + timedelta(days=30)
            redis_data = {
                "user_id": user.id,
                "anchor_id": anchor.uid,
                "anchor_name": anchor.username,
                "diamonds_paid": float(amount),
                "subscription_date": subscription_date.strftime('%Y-%m-%d %H:%M:%S'),
                "expiry_date": expiry_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            redis_client.set(redis_key, json.dumps(redis_data), ex=30 * 24 * 60 * 60)

        return JsonResponse({
            "code": 0,
            "message": "Subscription successful",
            "data": {
                "user_id": user.id,
                "anchor_id": anchor.uid,
                "subscription_date": subscription_date.strftime('%Y-%m-%d %H:%M:%S'),
                "diamonds_paid": float(amount),
                "expiry_date": expiry_date.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        return JsonResponse({
            "code": 1,
            "message": f"Internal server error: {str(e)}"
        }, status=500)
        
# 获取用户的所有有效订阅记录接口
@api_view(['GET'])
def get_subscriptions(request):
    """
    获取用户的所有有效订阅记录（只返回未过期的订阅）
    GET /api/subscribe/get_subscriptions
    """
    try:
        # 获取当前用户
        user = get_user(request)

        if not user:
            return JsonResponse({"code": 1, "message": "User not authenticated"}, status=400)

        user_id = user.id  # 从当前用户对象中获取 user_id

        # 构建Redis的前缀 key
        redis_key_prefix = f"subscription:{user_id}:"

        # 获取该用户所有订阅的 Redis key
        redis_client = get_redis_connection('subscribe')  # 使用 'subscribe' 配置连接到 Redis
        subscription_keys = redis_client.keys(f"{redis_key_prefix}*")  # 获取以 user_id 为前缀的所有订阅 key

        if not subscription_keys:
            return JsonResponse({"code": 1, "message": "No subscriptions found for this user"}, status=404)

        # 构建返回的订阅列表数据
        subscription_anchor_id_list = []
        live_status_list = []
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
                        anchor_id = redis_data.get("anchor_id")
                        room_infos = RoomInfo.objects.filter(uid=anchor_id)

                        if room_infos:
                            anchor_room_infos = []
                            username = ""
                            for room_info in room_infos:
                                username = room_info.user_name
                                anchor_room_infos.append({
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
                            live_status_list.append({
                                "uid":anchor_id,
                                "username":username,
                                "diamonds_paid": diamonds_paid,
                                "subscription_date": redis_data.get("subscription_date"),
                                "subscription_end_date": expiry_date_str,  # 返回原始的到期日期字符串
                                "anchor_room_infos":anchor_room_infos
                            })
        return Response({
            "code": 0,
            "data": {"lives_info": live_status_list}
        })


    except Exception as e:
        # 处理异常并返回 500 错误
        return JsonResponse({
            "code": 1,
            "message": f"Internal server error: {str(e)}"
        }, status=500)