from django.db import models
from django.contrib.auth.models import AbstractUser ,AbstractBaseUser, BaseUserManager
import uuid
import base64
from datetime import timedelta
from django.utils import timezone
#
# class ChatUser(AbstractUser):
#     '''聊天用户模型'''
#     nickname = models.CharField(max_length=32, verbose_name="昵称", blank=True)
#     phone = models.CharField(
#         max_length=11, null=True, verbose_name="手机号"
#     )
#     img = models.ImageField(
#         upload_to="headimage", blank=True, null=True, verbose_name="头像"
#     )
#
#     def __str__(self):
#         return self.username
#
#     class Meta:
#         verbose_name = "聊天用户信息"
#         verbose_name_plural = verbose_name
#
#
#
# class Room(models.Model):
#     '''聊天室模型'''
#     name = models.CharField(max_length=128)
#     online = models.ManyToManyField(to=ChatUser, blank=True)
#
#     def get_online_count(self):
#         return self.online.count()
#
#     def join(self, user):
#         self.online.add(user)
#         self.save()
#
#     def leave(self, user):
#         self.online.remove(user)
#         self.save()
#
#     def __str__(self):
#         return f'{self.name} ({self.get_online_count()})'
#
#     class Meta:
#         verbose_name = "聊天室信息"
#         verbose_name_plural = verbose_name
#
#
# class Message(models.Model):
#     '''消息模型'''
#     user = models.ForeignKey(to=ChatUser, on_delete=models.CASCADE)
#     room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
#     content = models.CharField(max_length=512)
#     timestamp = models.DateTimeField(auto_now_add=True)
#
#     def __str__(self):
#         return f'{self.user.username}: {self.content} [{self.timestamp}]'
#
#     class Meta:
#         verbose_name = "消息"
#         verbose_name_plural = verbose_name

def generate_short_uuid():
    u = uuid.uuid4()
    b64 = base64.urlsafe_b64encode(u.bytes).rstrip(b'=').decode('ascii')
    return b64

class Anchor(models.Model):
    uid = models.CharField(primary_key=True, max_length=22, default=generate_short_uuid, editable=False)
    username = models.CharField(max_length=150, unique=True)
    handle = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chatApp_anchor'


class ChatUser(AbstractBaseUser):
    id = models.AutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=254, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    nickname = models.CharField(max_length=32, blank=True)
    img = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=11, blank=True)

    # Google 登录相关字段
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Google 用户 ID
    avatar = models.URLField(max_length=255, blank=True, null=True)  # Google 头像 URL

    # 使用默认的模型管理器
    objects = models.Manager()

    # 登录字段
    USERNAME_FIELD = 'username'  # 登录时使用的字段
    REQUIRED_FIELDS = ['email']  # 注册时必须提供的字段（不包括用户名和密码）

    def __str__(self):
        return self.username

class ChatUserChatHistory(models.Model):
    room_name = models.CharField(max_length=255)
    uid = models.CharField(max_length=255, default='0')
    username = models.CharField(max_length=255)
    user_message = models.TextField()
    send_date = models.DateTimeField()
    identity = models.SmallIntegerField(default=0)  # 0: 游客，1: 正常用户

    class Meta:
        db_table = 'chatApp_chatuser_chat_history'  # 映射到正确的表名

class UserBalance(models.Model):
    user_id = models.IntegerField(unique=True, verbose_name="用户ID")  # 设置user_id为唯一字段
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="用户余额")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        db_table = 'user_balance'
        verbose_name = '用户余额'
        verbose_name_plural = '用户余额'

    def __str__(self):
        return f"User {self.user_id} Balance: {self.balance}"


    def deduct_balance(self, amount):
        """扣除用户余额"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()  # 保存更新后的余额
            return True
        return False

class RechargeRecord(models.Model):
    user_id = models.IntegerField(verbose_name="用户ID")  # 关联用户ID
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="充值金额")
    recharge_date = models.DateTimeField(auto_now_add=True, verbose_name="充值时间")
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='completed', verbose_name="充值状态")

    class Meta:
        db_table = 'recharge_records'
        verbose_name = '充值记录'
        verbose_name_plural = '充值记录'

    def __str__(self):
        return f"User {self.user_id} Recharge {self.amount} at {self.recharge_date}"

class DonationRecord(models.Model):
    user_id = models.IntegerField(verbose_name="用户ID")  # 赠送打赏的用户
    anchor_id = models.CharField(max_length=225, verbose_name="主播ID")  # 确保字段是 CharField，并且 max_length 匹配数据库中的长度
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="打赏金额")
    donation_date = models.DateTimeField(auto_now_add=True, verbose_name="打赏时间")
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='completed', verbose_name="打赏状态")

    class Meta:
        db_table = 'donation_records'
        verbose_name = '打赏记录'
        verbose_name_plural = '打赏记录'

    def __str__(self):
        return f"User {self.user_id} donated {self.amount} to Anchor {self.anchor_id} on {self.donation_date}"

class AnchorBalance(models.Model):
    anchor_id = models.CharField(max_length=225, verbose_name="主播ID")  # 确保字段是 CharField，并且 max_length 匹配数据库中的长度
    total_donations = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="主播收到的总打赏金额")
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="主播当前余额")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        db_table = 'anchor_balance'
        verbose_name = '主播余额'
        verbose_name_plural = '主播余额'

    def __str__(self):
        return f"Anchor {self.anchor_id} Total Donations: {self.total_donations} Balance: {self.balance}"

# 用户订阅模型
class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(ChatUser, on_delete=models.SET_NULL, null=True, blank=True)
    anchor = models.ForeignKey(Anchor, on_delete=models.SET_NULL, null=True, blank=True)
    diamonds_paid = models.DecimalField(max_digits=10, decimal_places=2)
    subscription_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'anchor']
        db_table = 'subscription'  # 显式指定表名

    def __str__(self):
        return f"{self.user.username} subscribed to {self.anchor.username}"



#用户关注/取消关注模型
class UserFollowedRoom(models.Model):
    user_id = models.IntegerField()  # 用户ID
    room_name = models.CharField(max_length=255)  # 直播间ID
    followed_at = models.DateTimeField(auto_now_add=True)  # 关注时间
    status = models.BooleanField(default=True)  # 关注状态，True 为关注，False 为取消关注



    class Meta:
        db_table = 'user_followed_room'  # 显式指定表名
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'room_name'], name='unique_user_room')
        ]

    def __str__(self):
        return f"User {self.user_id} follows room {self.room_name} (status: {self.status})"

class RoomInfo(models.Model):
    # 房间类型的选择项
    ROOM_TYPE_CHOICES = (
        (0, 'Free'),  # 免费房间
        (1, 'VIP'),   # VIP房间
        (2, '1v1'),   # 一对一房间
    )

    uid = models.CharField(max_length=255, verbose_name="用户ID")
    character_name = models.CharField(max_length=255, verbose_name="角色名称")
    title = models.CharField(max_length=255, verbose_name="房间标题")
    coin_num = models.IntegerField(verbose_name="钻石数量")
    room_type = models.SmallIntegerField(choices=ROOM_TYPE_CHOICES, default=0, verbose_name="房间类型")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="房间创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="房间最后更新时间")

    class Meta:
        db_table = 'room_info'  # 设置表名

    def __str__(self):
        return f"Room: {self.title} (UID: {self.uid}, Character: {self.character_name})"

class VipSubscriptionRecord(models.Model):
    user_id = models.IntegerField()  # 存储用户ID，不使用外键
    anchor_id = models.CharField(max_length=255)  # 存储主播ID，不使用外键
    room_name = models.CharField(max_length=255)  # 订阅的房间名称
    pay_coin_num = models.DecimalField(max_digits=10, decimal_places=2)  # 支付的钻石数量
    subscription_date = models.DateTimeField(auto_now_add=True)  # 订阅时间

    class Meta:
        db_table = 'vip_subscription_record'  # 显式指定表名

    def __str__(self):
        return f"User {self.user_id} subscribed to Room {self.room_name} with {self.pay_coin_num} coins"