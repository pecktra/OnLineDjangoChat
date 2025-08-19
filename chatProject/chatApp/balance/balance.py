from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum
from chatApp.models import DonationRecord, Anchor,AnchorBalance, ChatUser,UserBalance  # 假设已经定义了相关模型
from rest_framework import status
from django.db import transaction
from decimal import Decimal

# 获取用户的所有打赏记录
@api_view(['GET'])
def get_user_donations(request):
    """
    获取用户的所有打赏记录
    GET /api/donations/user/?user_id=<user_id>
    """
    user_id = request.GET.get('user_id')  # 从查询参数中获取 user_id

    if not user_id:
        return Response({"code": 1, "message": "Missing user_id parameter."}, status=400)

    try:
        # 查询用户的所有打赏记录
        donations = DonationRecord.objects.filter(user_id=user_id).order_by('-donation_date')

        if not donations:
            return Response({"code": 1, "message": "No donations found for this user."}, status=404)

        donation_data = []
        for donation in donations:
            # 手动查询关联的主播信息
            anchor = Anchor.objects.filter(uid=donation.anchor_id).first()  # 使用 anchor_id 查询 Anchor 表
            if anchor:
                anchor_name = anchor.username  # 获取主播名称
            else:
                anchor_name = "Unknown"  # 如果找不到主播，使用默认值

            # 将打赏信息与主播名称一起返回
            donation_data.append({
                "donation_id": donation.id,
                "anchor_name": anchor_name,  # 返回主播名称
                "donation_amount": donation.amount,
                "donation_date": donation.donation_date
            })

        return Response({
            "code": 0,
            "data": {
                "user_donations": donation_data
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

# 获取主播收到的所有打赏记录
@api_view(['GET'])
def get_anchor_donations(request):
    """
    获取主播收到的所有打赏记录
    GET /api/donations/anchor/?anchor_id=<anchor_id>
    """
    anchor_id = request.GET.get('anchor_id')  # 从查询参数中获取 anchor_id

    if not anchor_id:
        return Response({"code": 1, "message": "Missing anchor_id parameter."}, status=400)

    try:
        # 查询主播的所有打赏记录
        donations = DonationRecord.objects.filter(anchor_id=anchor_id).order_by('-donation_date')

        if not donations:
            return Response({"code": 1, "message": "No donations found for this anchor."}, status=404)

        # 获取打赏记录和用户信息
        donation_data = []
        for donation in donations:
            # 手动查找关联用户信息
            user = ChatUser.objects.filter(id=donation.user_id).first()  # 根据 user_id 查找用户
            user_name = user.username if user else "Unknown"  # 如果找不到用户，返回 "Unknown"

            donation_data.append({
                "donation_id": donation.id,
                "user_name": user_name,
                "donation_amount": donation.amount,
                "donation_date": donation.donation_date
            })

        return Response({
            "code": 0,
            "data": {
                "anchor_donations": donation_data
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


# 获取用户的总打赏金额
@api_view(['GET'])
def get_user_total_donated(request):
    """
    获取用户的总打赏金额
    GET /api/donations/user/total/?user_id=<user_id>
    """
    user_id = request.GET.get('user_id')  # 从查询参数中获取 user_id

    if not user_id:
        return Response({"code": 1, "message": "Missing user_id parameter."}, status=400)

    try:
        # 查询该用户的总打赏金额
        total_donated = DonationRecord.objects.filter(user_id=user_id).aggregate(Sum('amount'))['amount__sum']

        if total_donated is None:
            return Response({"code": 1, "message": "No donations found for this user."}, status=404)

        return Response({
            "code": 0,
            "data": {
                "total_donated": total_donated
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)


# 获取主播的总收到打赏金额
@api_view(['GET'])
def get_anchor_total_received(request):
    """
    获取主播的总收到打赏金额
    GET /api/donations/anchor/total/?anchor_id=<anchor_id>
    """
    anchor_id = request.GET.get('anchor_id')  # 从查询参数中获取 anchor_id

    if not anchor_id:
        return Response({"code": 1, "message": "Missing anchor_id parameter."}, status=400)

    try:
        # 查询该主播的总收到打赏金额
        total_received = DonationRecord.objects.filter(anchor_id=anchor_id).aggregate(Sum('amount'))['amount__sum']

        if total_received is None:
            return Response({"code": 1, "message": "No donations found for this anchor."}, status=404)

        return Response({
            "code": 0,
            "data": {
                "total_received": total_received
            }
        })

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"}, status=500)

@api_view(['POST'])
def make_donation(request):
    """
    用户打赏主播
    POST /api/donations/make/
    """
    try:
        # 获取请求数据
        user_id = request.data.get('user_id')  # 用户ID
        anchor_id = request.data.get('anchor_id')  # 主播ID
        amount = request.data.get('amount')  # 打赏金额

        # 检查参数是否缺失
        if not user_id or not anchor_id or not amount:
            return Response({"code": 1, "message": "Missing required parameters."}, status=status.HTTP_400_BAD_REQUEST)

        # 确保金额大于0
        try:
            amount = Decimal(amount)  # 将金额转换为Decimal类型（避免类型错误）
        except ValueError:
            return Response({"code": 1, "message": "Invalid amount format."}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({"code": 1, "message": "Amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

        # 获取用户余额
        user_balance = UserBalance.objects.filter(user_id=user_id).first()
        if not user_balance:
            return Response({"code": 1, "message": "User balance not found."}, status=status.HTTP_404_NOT_FOUND)

        # 获取用户名称
        user = ChatUser.objects.filter(id=user_id).first()
        if not user:
            return Response({"code": 1, "message": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        user_name = user.username  # 假设 `username` 字段存储用户的名称

        # 检查用户余额是否足够
        if user_balance.balance < amount:
            return Response({"code": 1, "message": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

        # 获取主播余额，如果没有，则创建一个初始余额为0的记录
        anchor_balance = AnchorBalance.objects.filter(anchor_id=anchor_id).first()
        if not anchor_balance:
            anchor_balance = AnchorBalance.objects.create(
                anchor_id=anchor_id,
                balance=Decimal('0.00'),
                total_donations=Decimal('0.00')
            )

        # 获取主播信息
        anchor = Anchor.objects.filter(uid=anchor_id).first()
        if not anchor:
            return Response({"code": 1, "message": "Anchor not found."}, status=status.HTTP_404_NOT_FOUND)
        anchor_name = anchor.username  # 假设 `username` 字段存储主播的名称

        # 使用事务来保证数据库的一致性
        with transaction.atomic():
            # 扣除用户余额
            user_balance.balance -= amount
            user_balance.save()

            # 更新主播余额和总打赏金额
            anchor_balance.balance += amount  # 更新主播余额
            anchor_balance.total_donations += amount  # 更新总打赏金额
            anchor_balance.save()

            # 创建 DonationRecord 记录打赏信息
            donation_record = DonationRecord.objects.create(
                user_id=user_id,
                anchor_id=anchor_id,
                amount=amount,
                status='completed'  # 设置打赏状态为 completed
            )

        # 返回成功的响应
        return Response({
            "code": 0,
            "message": "Donation successful.",
            "data": {
                "donation_id": donation_record.id,
                "user_name": user_name,  # 返回用户名
                "anchor_name": anchor_name,  # 返回主播名称
                "amount": amount,
                "donation_date": donation_record.donation_date,
                "remaining_balance": user_balance.balance  # 返回扣除后的余额
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"code": 1, "message": f"Internal server error: {str(e)}"},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)