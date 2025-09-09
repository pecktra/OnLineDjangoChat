import uuid
import json
import hmac
import hashlib
import requests
import qrcode
from io import BytesIO
import base64
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.utils import timezone
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from chatApp.models import UserBalance, PaymentRechargeRecord,PaymentLog
from django.http import JsonResponse
import requests

# NOWPayments 配置
NOWPAYMENTS_API_KEY = settings.NOWPAYMENTS_API_KEY
IPN_SECRET_KEY = settings.NOWPAYMENTS_IPN_SECRET_KEY
NOWPAYMENTS_API_URL = 'https://api.nowpayments.io/v1'

def generate_qr_code(pay_address):
    """
    生成二维码，内容为裸地址
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(pay_address)  # 只使用地址
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    return img


def convert_image_to_base64(image):
    """
    将二维码图像转换为 Base64 编码
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


@api_view(['POST'])
def process_recharge(request):
    """
    处理充值请求，创建充值记录，调用 NOWPayments API 生成支付地址
    """
    crypto_amount = request.data.get("crypto_amount")
    user_id = request.data.get("user_id")

    # 日志记录请求
    PaymentLog.objects.create(
        log_type="api_request",
        user_id=user_id,
        details=f"Request to initiate recharge: crypto_amount={crypto_amount}"
    )

    if crypto_amount not in [12, 20, 100]:
        return JsonResponse({"code": 1, "error": "crypto_amount must be 12, 20, or 100 USDT"}, status=400)

    if not user_id:
        return JsonResponse({"code": 1, "error": "Missing user_id parameter"}, status=400)

    # 计算平台货币
    amount = crypto_amount * 5
    if crypto_amount == 100:
        amount += 50

    order_id = str(uuid.uuid4())
    currency = "USD"
    crypto_currency = "USDTTRC20"
    status = "waiting"

    user_balance, created = UserBalance.objects.get_or_create(
        user_id=user_id,
        defaults={"balance": 0, "last_updated": timezone.now()}
    )
    if not created:
        user_balance.updated_at = timezone.now()
        user_balance.save()

    try:
        response = requests.post(
            f"{NOWPAYMENTS_API_URL}/payment",
            headers={"x-api-key": settings.NOWPAYMENTS_API_KEY},
            json={
                "price_amount": float(crypto_amount),
                "price_currency": currency,
                "pay_currency": crypto_currency.lower(),
                "order_id": order_id,
                "order_description": f"Recharge {crypto_amount} USDT for user {user_id}",
                "ipn_callback_url": settings.NOWPAYMENTS_IPN_CALLBACK_URL
            }
        )
        response.raise_for_status()
        payment_data = response.json()

        # 日志记录 API 响应
        PaymentLog.objects.create(
            log_type="api_response",
            user_id=user_id,
            order_id=order_id,
            details=f"NOWPayments response: {json.dumps(payment_data)}"
        )

        payment_id = payment_data.get("payment_id")
        pay_address = payment_data.get("pay_address")
        pay_amount = payment_data.get("pay_amount")

        if not payment_id or not pay_address:
            return JsonResponse({"code": 1, "error": "Failed to retrieve payment data from NOWPayments"}, status=500)

        recharge_record = PaymentRechargeRecord.objects.create(
            user_id=user_id,
            amount=amount,
            currency=currency,
            crypto_amount=crypto_amount,
            crypto_currency=crypto_currency,
            order_id=order_id,
            payment_id=payment_id,
            recharge_date=timezone.now(),
            status=status
        )

        qr_code_image = generate_qr_code(pay_address)
        qr_code_base64 = convert_image_to_base64(qr_code_image)

        return JsonResponse({
            "code": 0,
            "message": "Recharge initiated, waiting for confirmation",
            "order_id": order_id,
            "payment_id": payment_id,
            "pay_address": pay_address,
            "pay_amount": pay_amount,
            "qr_code": qr_code_base64
        }, status=200)

    except requests.RequestException as e:
        PaymentLog.objects.create(
            log_type="error",
            user_id=user_id,
            details=f"Failed to create payment: {str(e)}"
        )
        return JsonResponse({"code": 1, "error": f"Failed to create payment: {str(e)}"}, status=500)


@csrf_exempt
def payment_callback(request):
    """
    NOWPayments回调处理，更新余额和充值记录，并写日志
    """
    if request.method != 'POST':
        return JsonResponse({'code': 1, 'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        payment_id = data.get('payment_id')
        order_id = data.get('order_id')
        status = data.get('payment_status')
        amount = data.get('actually_paid')
        user_id = data.get('order_description', '').split('user ')[-1]

        # 日志记录 IPN 回调
        PaymentLog.objects.create(
            log_type="ipn",
            user_id=user_id,
            order_id=order_id,
            details=f"Received IPN callback: {json.dumps(data)}"
        )

        received_signature = request.headers.get('x-nowpayments-sig')
        sorted_payload = json.dumps(data, separators=(',', ':'), sort_keys=True)
        computed_signature = hmac.new(
            key=settings.IPN_SECRET_KEY.encode('utf-8'),
            msg=sorted_payload.encode('utf-8'),
            digestmod=hashlib.sha512
        ).hexdigest()

        if received_signature != computed_signature:
            return JsonResponse({'code': 1, 'error': 'Invalid signature'}, status=400)

        if status != 'finished':
            return JsonResponse({'code': 1, 'error': f'Payment not finished, status: {status}'}, status=400)

        recharge_record = PaymentRechargeRecord.objects.get(order_id=order_id, status='waiting')
        user_balance = UserBalance.objects.get(user_id=user_id)

        with transaction.atomic():
            user_balance.add_balance(recharge_record.amount)
            recharge_record.status = 'confirmed'
            recharge_record.payment_id = payment_id
            recharge_record.save()

        return JsonResponse({'code': 0, 'message': 'Payment confirmed'}, status=200)

    except Exception as e:
        PaymentLog.objects.create(
            log_type="error",
            user_id=user_id if 'user_id' in locals() else None,
            order_id=order_id if 'order_id' in locals() else None,
            details=f"Error in payment callback: {str(e)}"
        )
        return JsonResponse({'code': 1, 'error': f'An error occurred: {str(e)}'}, status=500)


@api_view(['GET'])
def check_payment_status(request, order_id):
    """
    检查支付状态，并写日志
    """
    try:
        recharge_record = PaymentRechargeRecord.objects.get(order_id=order_id)

        PaymentLog.objects.create(
            log_type="api_request",
            order_id=order_id,
            user_id=recharge_record.user_id,
            details=f"Check payment status: {recharge_record.status}"
        )

        return JsonResponse({
            'code': 0,
            'status': recharge_record.status,
            'message': 'Status retrieved'
        }, status=200)
    except PaymentRechargeRecord.DoesNotExist:
        return JsonResponse({'code': 1, 'error': 'Recharge record not found'}, status=404)