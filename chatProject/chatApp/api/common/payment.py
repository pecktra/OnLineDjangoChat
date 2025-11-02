from django.db import transaction
from decimal import Decimal
from chatApp.models import Anchor,AnchorBalance, ChatUser,UserBalance , PaymentExpenditureRecord ,PaymentDiamondFlow


def process_diamond_payment(user_id, anchor_id=None, amount=None, payment_type=None, payment_source=None, details=None):
    """
    通用钻石支付处理逻辑：
    扣除用户钻石，更新主播余额，写入支出记录和统一流水表。

    参数：
        user_id: 用户ID
        anchor_id: 主播ID（可选，比如打赏或进入房间）
        amount: 支付金额（Decimal或float）
        payment_type: 支付类型（如 'donation'、'room_entry'、'subscription' 等）
        payment_source: 支付来源（建议与 payment_type 相同）
        details: 附加说明（例如“进入VIP房间 XXX”）

    返回：
        expenditure_record: PaymentExpenditureRecord 对象
    """
    if amount is None or Decimal(amount) <= 0:
        raise ValueError("Amount must be greater than 0")

    amount = Decimal(amount)

    # 获取用户余额
    user_balance = UserBalance.objects.filter(user_id=user_id).first()
    if not user_balance:
        raise ValueError("User balance not found")

    if user_balance.balance < amount:
        raise ValueError("Insufficient balance")

    # 获取或创建主播余额
    anchor_balance = None
    if anchor_id:
        anchor_balance = AnchorBalance.objects.filter(anchor_id=anchor_id).first()
        if not anchor_balance:
            anchor_balance = AnchorBalance.objects.create(
                anchor_id=anchor_id,
                balance=Decimal('0.00'),
                total_received=Decimal('0.00')
            )

    with transaction.atomic():
        # 扣用户余额
        user_balance.balance -= amount
        user_balance.save()

        # 增加主播余额
        if anchor_balance:
            anchor_balance.balance += amount
            anchor_balance.total_received += amount
            anchor_balance.save()

        # 创建支出记录
        expenditure_record = PaymentExpenditureRecord.objects.create(
            user_id=user_id,
            anchor_id=anchor_id,
            payment_type=payment_type,
            payment_source=payment_source,  # ✅ 保留字段
            amount=amount,
            currency='ZS'
        )

        # 写统一流水表
        PaymentDiamondFlow.objects.create(
            user_id=user_id,
            anchor_id=anchor_id,
            payment_action=payment_type,
            amount=amount,
            currency='ZS',
            details=details
        )

    return expenditure_record


def process_referral_reward(invitee_id, referrer_id, reward_amount=Decimal('10.00')):
    """
    邀请奖励处理逻辑：
    被邀请人与邀请人各获得钻石奖励，并写入统一流水表。

    参数：
        invitee_id: 被邀请人用户ID
        referrer_id: 邀请人用户ID
        reward_amount: 每人获得的钻石数量（默认10）

    返回：
        True 成功 / False 失败
    """
    try:
        reward_amount = Decimal(reward_amount)

        # 获取或创建被邀请人余额
        invitee_balance, _ = UserBalance.objects.get_or_create(
            user_id=invitee_id, defaults={'balance': Decimal('0.00')}
        )
        # 获取或创建邀请人余额
        referrer_balance, _ = UserBalance.objects.get_or_create(
            user_id=referrer_id, defaults={'balance': Decimal('0.00')}
        )

        with transaction.atomic():
            # --- 被邀请人增加余额并写入流水 ---
            invitee_balance.balance += reward_amount
            invitee_balance.save()
            PaymentDiamondFlow.objects.create(
                user_id=invitee_id,
                anchor_id=None,
                payment_action='other',
                amount=reward_amount,
                currency='ZS',
                details=f"通过用户 {referrer_id} 的邀请获得 {reward_amount} 钻石奖励"
            )

            # --- 邀请人增加余额并写入流水 ---
            referrer_balance.balance += reward_amount
            referrer_balance.save()
            PaymentDiamondFlow.objects.create(
                user_id=referrer_id,
                anchor_id=None,
                payment_action='other',
                amount=reward_amount,
                currency='ZS',
                details=f"邀请用户 {invitee_id} 注册获得 {reward_amount} 钻石奖励"
            )

        print(f"[Referral Reward] 用户 {invitee_id} 与 {referrer_id} 各获得 {reward_amount} 钻石奖励。")
        return True

    except Exception as e:
        print(f"[Referral Reward Error] {e}")
        return False