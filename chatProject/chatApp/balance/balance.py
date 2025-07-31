from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum
from chatApp.models import DonationRecord, Anchor, ChatUser  # 假设已经定义了相关模型


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
        donations = DonationRecord.objects.filter(user_id=user_id).select_related('anchor').order_by('-donation_date')

        if not donations:
            return Response({"code": 1, "message": "No donations found for this user."}, status=404)

        donation_data = [
            {
                "donation_id": donation.id,
                "anchor_name": donation.anchor.name,
                "donation_amount": donation.amount,
                "donation_date": donation.donation_date
            }
            for donation in donations
        ]

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
        donations = DonationRecord.objects.filter(anchor_id=anchor_id).select_related('user').order_by('-donation_date')

        if not donations:
            return Response({"code": 1, "message": "No donations found for this anchor."}, status=404)

        donation_data = [
            {
                "donation_id": donation.id,
                "user_name": donation.user.username,
                "donation_amount": donation.amount,
                "donation_date": donation.donation_date
            }
            for donation in donations
        ]

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
