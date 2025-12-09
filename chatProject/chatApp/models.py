from django.db import models
from django.contrib.auth.models import AbstractUser, AbstractBaseUser, BaseUserManager
import uuid
import base64
from datetime import timedelta
from django.utils import timezone


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


def character_image_upload_path(instance, filename):
    """
    动态生成图片上传路径，例如：
    <username>/characters/<filename>
    """
    return os.path.join(instance.username, 'characters', filename)



def creator_character_image_upload_path(instance, filename):
    """
    动态生成图片上传路径，例如：
    <username>/characters/<filename>
    """
    return os.path.join('creator',instance.username, "aaaaa",'characters', filename)


class CharacterCard(models.Model):
    uid = models.CharField(max_length=150, verbose_name="用户ID")  # 用户id
    username = models.CharField(max_length=150, verbose_name="用户名")  # 用户名
    character_name = models.CharField(max_length=150, verbose_name="角色卡名称")  # 角色卡名称
    image_name = models.CharField(max_length=150, verbose_name="图片名称")  # 图片名称
    image_path = models.ImageField(
        upload_to=character_image_upload_path,  # 图片存储路径函数
        max_length=255,
        verbose_name="图片存储路径"
    )
    character_data = models.TextField(verbose_name="角色数据（JSON格式）")  # 角色数据
    create_date = models.CharField(max_length=150, verbose_name="上传时间")  # 上传时间

    # 新增字段
    language = models.CharField(
        max_length=2,
        choices=[('en', 'English'), ('cn', '中文')],
        default='en',
        verbose_name="语言"
    )
    tags = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="标签（逗号分隔或JSON）"
    )
    source = models.CharField(
        max_length=2,
        choices=[('st', 'ST端'), ('pt', 'PT端')],
        default='pt',
        verbose_name="数据来源"
    )

    class Meta:
        db_table = 'character_card'
        verbose_name = "角色卡"
        verbose_name_plural = "角色卡"



class CreatorCharacterCard(models.Model):
    uid = models.CharField(max_length=150, verbose_name="用户ID")  # 用户id
    username = models.CharField(max_length=150, verbose_name="用户名")  # 用户名
    room_id = models.CharField(max_length=255)
    character_name = models.CharField(max_length=150, verbose_name="角色卡名称")  # 角色卡名称
    image_path = models.CharField(
        max_length=255,
        verbose_name="图片存储路径"
    )

    is_public = models.IntegerField(max_length=150, verbose_name="是否公开，0不公开，1公开")  # 上传时间
    preset_id = models.IntegerField(max_length=150, verbose_name="预设id")  # 上传时间
    character_data = models.TextField(default=dict)  # 角色数据
    create_date = models.CharField(max_length=150, verbose_name="上传时间")  # 上传时间


    tags = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="标签（逗号分隔或JSON）"
    )


    class Meta:
        db_table = 'creator_character_card'
        verbose_name = "创作者角色卡"
        verbose_name_plural = "创作者角色卡"


class RoomImageBinding(models.Model):
    uid = models.CharField(max_length=150, null=True, blank=True)
    room_id = models.CharField(max_length=255, verbose_name="房间ID")
    image_id = models.IntegerField(verbose_name="图片ID")  # 对应 CharacterCard 的自增 id
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="绑定时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "room_image_binding"
        verbose_name = "房间默认图片绑定"
        verbose_name_plural = "房间默认图片绑定"
        indexes = [
            models.Index(fields=["room_id"], name="idx_room_id"),
            models.Index(fields=["image_id"], name="idx_image_id")
        ]

    def __str__(self):
        return f"Room {self.room_id} → Image ID {self.image_id}"


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

    referrer_id = models.BigIntegerField(null=True, blank=True, verbose_name="邀请人ID")
    # 登录字段
    USERNAME_FIELD = 'username'  # 登录时使用的字段
    REQUIRED_FIELDS = ['email']  # 注册时必须提供的字段（不包括用户名和密码）

    def __str__(self):
        return self.username


class ChatUserChatHistory(models.Model):
    room_id = models.CharField(max_length=255, null=True)
    room_name = models.CharField(max_length=255)
    uid = models.CharField(max_length=255, default='0')
    username = models.CharField(max_length=255)
    user_message = models.TextField()
    send_date = models.DateTimeField()
    identity = models.SmallIntegerField(default=0)  # 0: 游客，1: 正常用户

    class Meta:
        db_table = 'chatApp_chatuser_chat_history'  # 映射到正确的表名


class UserBalance(models.Model):
    user_id = models.IntegerField(unique=True, null=False, verbose_name="用户ID")
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台货币余额"
    )
    usdt_balance = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=0.00000000,
        verbose_name="USDT余额"
    )
    bonus_balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        verbose_name="平台货币赠送余额（兑换优惠赠送的金额）"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新时间"
    )

    class Meta:
        db_table = 'payment_user_balance'
        indexes = [
            models.Index(fields=['user_id'])
        ]
        verbose_name = "用户余额"
        verbose_name_plural = "用户余额"

    def __str__(self):
        return f"User {self.user_id} Balance"

    def add_balance(self, amount, is_bonus=False):
        """增加余额（平台货币或赠送余额）"""
        if amount > 0:
            if is_bonus:
                self.bonus_balance += amount  # 增加赠送余额
            else:
                self.balance += amount  # 增加平台货币余额
            self.save()  # 保存更新后的余额
            return True
        return False

    def deduct_balance(self, amount):
        """扣除用户余额"""
        if self.balance >= amount:
            self.balance -= amount
            self.save()  # 保存更新后的余额
            return True
        return False


class AnchorBalance(models.Model):
    anchor_id = models.CharField(max_length=22, unique=True, verbose_name="主播ID")  # 与数据库一致，最大长度为22
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="平台货币余额（USD等值）")
    usdt_balance = models.DecimalField(max_digits=18, decimal_places=8, default=0.00000000, verbose_name="USDT余额")
    total_received = models.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                         verbose_name="累计收入（USD等值）")
    last_updated = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")  # 自动更新时间

    class Meta:
        db_table = 'payment_anchor_balance'  # 对应数据库中的表名
        verbose_name = '主播余额'
        verbose_name_plural = '主播余额'
        indexes = [
            models.Index(fields=['anchor_id'])  # 为 anchor_id 创建索引
        ]

    def __str__(self):
        return f"Anchor {self.anchor_id} Total Received: {self.total_received} Balance: {self.balance} USDT Balance: {self.usdt_balance}"


# 用户关注/取消关注模型
class UserFollowRelation(models.Model):
    follower_id = models.CharField(max_length=255)  # 关注发起方用户ID
    followed_id = models.CharField(max_length=255)  # 被关注方用户ID
    followed_at = models.DateTimeField(auto_now_add=True)  # 关注时间
    status = models.BooleanField(default=True)  # 关注状态：True 为关注，False 为取消关注

    class Meta:
        db_table = 'user_follow_relation'  # 显式指定表名
        constraints = [
            models.UniqueConstraint(fields=['follower_id', 'followed_id'], name='unique_user_follow')
        ]

    def __str__(self):
        return f"User {self.follower_id} follows user {self.followed_id} (status: {self.status})"


class RoomInfo(models.Model):
    # 房间类型的选择项
    ROOM_TYPE_CHOICES = (
        (0, 'Free'),  # 免费房间
        (1, 'VIP'),  # VIP房间
        (2, '1v1'),  # 一对一房间
    )

    uid = models.CharField(max_length=255, verbose_name="主播ID")
    user_name = models.CharField(max_length=255, null=True, verbose_name="主播名称")
    room_id = models.CharField(max_length=255, null=True, verbose_name="房间ID")
    room_name = models.CharField(max_length=255, null=True, verbose_name="房间名称")
    character_name = models.CharField(max_length=255, verbose_name="角色名称")
    character_date = models.CharField(max_length=255, default=timezone.now, verbose_name="角色卡创建时间")
    title = models.CharField(max_length=255, verbose_name="房间标题")
    describe = models.CharField(max_length=255, null=True, verbose_name="房间描述")
    coin_num = models.IntegerField(verbose_name="钻石数量")
    room_type = models.SmallIntegerField(choices=ROOM_TYPE_CHOICES, default=0, verbose_name="房间类型")
    file_name = models.CharField(max_length=255, null=True, verbose_name="文件名")
    file_branch = models.CharField(max_length=255, null=True, verbose_name="文件分支")
    is_show = models.IntegerField(default=0, verbose_name="是否展示")
    is_info = models.IntegerField(verbose_name="是否添加info", null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="房间创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="房间最后更新时间")
    last_ai_reply_timestamp = models.FloatField(default=0, verbose_name="最后 AI 回复时间戳")
    weight = models.IntegerField(default=0, verbose_name="房间权重")  # 新增字段

    class Meta:
        db_table = 'room_info'  # 设置表名

    def __str__(self):
        return f"Room: {self.title} (UID: {self.uid}, Character: {self.character_name})"


class PaymentRechargeRecord(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('confirming', 'Confirming'),
        ('confirmed', 'Confirmed'),
        ('sending', 'Sending'),
        ('partially_paid', 'Partially Paid'),
        ('finished', 'Finished'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    payment_id = models.CharField(max_length=100, unique=True, verbose_name="NOWPayments 支付ID")
    user_id = models.IntegerField(verbose_name="用户ID")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="充值金额")
    currency = models.CharField(max_length=10, default='USD', verbose_name="充值货币")
    crypto_amount = models.DecimalField(max_digits=18, decimal_places=8, verbose_name="USDT充值金额")
    crypto_currency = models.CharField(max_length=10, default='USDT', verbose_name="加密货币类型，固定为USDT")
    order_id = models.CharField(max_length=100, unique=True, verbose_name="订单ID")
    recharge_date = models.DateTimeField(auto_now_add=True, verbose_name="充值时间")  # auto_now_add=True 会设置为当前时间
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='waiting',
        verbose_name="充值状态"
    )

    class Meta:
        db_table = 'payment_recharge_records'  # 与数据库表名一致
        verbose_name = '充值记录'
        verbose_name_plural = '充值记录'

    def __str__(self):
        return f"Payment {self.payment_id} - {self.status}"


class PaymentExpenditureRecord(models.Model):
    """
    支出记录表（打赏、订阅主播）
    """
    PAYMENT_TYPE_CHOICES = [
        ("donation", "打赏"),
        ("subscription", "订阅"),
    ]

    PAYMENT_SOURCE_CHOICES = [
        ("donation", "打赏"),
        ("subscription", "订阅"),
    ]

    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField(verbose_name="用户ID")
    anchor_id = models.CharField(max_length=22, verbose_name="主播ID")
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, verbose_name="支付类型")
    payment_source = models.CharField(max_length=20, choices=PAYMENT_SOURCE_CHOICES, verbose_name="支付来源")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="支付金额")
    currency = models.CharField(max_length=10, default="ZS", verbose_name="支付货币")
    payment_date = models.DateTimeField(default=timezone.now, verbose_name="支付时间")

    class Meta:
        db_table = "payment_expenditure_records"
        verbose_name = "支出,订阅记录"
        verbose_name_plural = "支出,订阅记录"


class PaymentLiveroomEntryRecord(models.Model):
    """
    直播间进入记录表
    """
    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField(verbose_name="用户ID")
    anchor_id = models.CharField(max_length=22, verbose_name="主播ID")
    room_name = models.CharField(max_length=255, verbose_name="房间名称")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="支付金额")
    currency = models.CharField(max_length=10, default="ZS", verbose_name="支付货币")

    class Meta:
        db_table = "payment_liveroom_entry_records"
        verbose_name = "直播间进入记录"
        verbose_name_plural = "直播间进入记录"


class PaymentLog(models.Model):
    """
    支付日志表
    """
    LOG_TYPE_CHOICES = [
        ("api_request", "API请求"),
        ("api_response", "API响应"),
        ("ipn", "回调通知"),
        ("error", "错误"),
    ]

    id = models.BigAutoField(primary_key=True)
    log_type = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES, verbose_name="日志类型")
    order_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="订单ID")
    user_id = models.IntegerField(null=True, blank=True, verbose_name="用户ID")
    details = models.TextField(verbose_name="日志详情")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

    class Meta:
        db_table = "payment_logs"
        verbose_name = "支付日志"
        verbose_name_plural = "支付日志"


class ForkRelation(models.Model):
    id = models.BigAutoField(primary_key=True)  # bigint 自增主键
    from_user_id = models.IntegerField(verbose_name="发起 fork 用户ID")
    target_id = models.CharField(max_length=22, verbose_name="被 fork 用户ID")
    room_id = models.CharField(max_length=255, verbose_name="原房间ID")
    character_name = models.CharField(max_length=255, verbose_name="角色名")
    floor = models.IntegerField(default=0, verbose_name="楼层")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "fork_relation"
        verbose_name = "Fork 关系"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"ForkRelation {self.id} from {self.from_user_id} to {self.target_id}"


class ForkTrace(models.Model):
    """
    记录 fork 链路信息
    """
    # 源头房间信息（最初的房间）
    source_room_id = models.CharField(max_length=32)
    source_uid = models.CharField(max_length=22)

    # 上一层房间信息（当前被 fork 的房间）
    prev_room_id = models.CharField(max_length=32)
    prev_uid = models.CharField(max_length=22)

    # 当前新 fork 房间信息
    current_room_id = models.CharField(max_length=32)
    current_uid = models.CharField(max_length=22)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fork_trace'


class Favorite(models.Model):
    id = models.BigAutoField(primary_key=True)
    uid = models.CharField(max_length=150, verbose_name="用户ID")
    room_id = models.CharField(max_length=150, verbose_name="角色卡 room_id")
    status = models.SmallIntegerField(default=1, verbose_name="收藏状态")  # 1=已收藏, 0=取消收藏
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "favorite"
        unique_together = ("uid", "room_id")
        verbose_name = "收藏"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"UID {self.uid} 收藏房间 {self.room_id} 状态 {self.status}"


class PaymentDiamondFlow(models.Model):
    PAYMENT_ACTION_CHOICES = (
        ('donation', 'Donation'),
        ('subscription', 'Subscription'),
        ('room_entry', 'Room Entry'),
        ('gift', 'Gift'),
        ('other', 'Other'),
    )

    user_id = models.IntegerField(verbose_name="用户ID")
    anchor_id = models.CharField(max_length=22, null=True, blank=True, verbose_name="主播ID")
    payment_action = models.CharField(
        max_length=20,
        choices=PAYMENT_ACTION_CHOICES,
        verbose_name="消费类型"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="支付金额")
    currency = models.CharField(max_length=10, default="ZS", verbose_name="支付货币")
    details = models.CharField(max_length=255, null=True, blank=True, verbose_name="附加信息")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="支付时间")

    class Meta:
        db_table = "payment_diamond_flow"
        verbose_name = "平台币流水"
        verbose_name_plural = verbose_name


class IPBlacklist(models.Model):
    """
    IP 黑名单表：记录被封禁的 IP 及其访问的接口
    """
    ip = models.GenericIPAddressField(verbose_name="IP 地址", unique=True)
    path = models.CharField(max_length=255, null=True, blank=True, verbose_name="访问接口路径")
    reason = models.CharField(max_length=255, null=True, blank=True, verbose_name="封禁原因")
    is_active = models.BooleanField(default=True, verbose_name="是否启用封禁")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

    class Meta:
        db_table = "ip_blacklist"
        verbose_name = "IP 黑名单"
        verbose_name_plural = "IP 黑名单"

    def __str__(self):
        return f"{self.ip} - {'封禁中' if self.is_active else '已解封'}"


class Preset(models.Model):
    """
    主播预设
    """
    room_id = models.CharField(max_length=255, verbose_name="room_id")
    preset_settings_openai = models.CharField(max_length=255, verbose_name="预设名称")
    temp_openai = models.FloatField(max_length=10, verbose_name="")
    top_k_openai = models.IntegerField(max_length=10, verbose_name="")
    top_p_openai = models.FloatField(max_length=10, verbose_name="")
    openai_max_context = models.IntegerField(max_length=10, verbose_name="")
    openai_max_tokens = models.IntegerField(max_length=10, verbose_name="")
    google_model = models.CharField(max_length=255, verbose_name="模型名称")
    model_n = models.IntegerField(max_length=10, verbose_name="")
    preset_json = models.TextField(verbose_name="")

    class Meta:
        db_table = "preset"


class CreatorPreset(models.Model):
    preset_settings_openai = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="OpenAI 预设名称"
    )
    temp_openai = models.FloatField(
        null=True,
        blank=True,
        help_text="OpenAI 温度"
    )
    top_k_openai = models.IntegerField(
        null=True,
        blank=True,
        help_text="OpenAI Top K"
    )
    top_p_openai = models.FloatField(
        null=True,
        blank=True,
        help_text="OpenAI Top P"
    )
    openai_max_context = models.IntegerField(
        null=True,
        blank=True,
        help_text="OpenAI 最大上下文长度"
    )
    openai_max_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text="OpenAI 最大输出 Token"
    )
    google_model = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="谷歌模型"
    )
    model_n = models.IntegerField(
        null=True,
        blank=True,
        help_text="模型数量"
    )
    preset_json = models.JSONField(
        null=True,
        blank=True,
        default=dict,  # 新增记录时默认空字典
        help_text="预设 JSON 配置（支持超大内容，已改为 MySQL JSON 类型）"
    )
    image = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="图片地址"
    )

    class Meta:
        db_table = 'creator_preset'
        verbose_name = '创作者中心模型预设'
        verbose_name_plural = '创作者中心模型预设'
        indexes = [
            models.Index(fields=['preset_settings_openai'], name='idx_preset_settings_openai'),
            models.Index(fields=['google_model'], name='idx_google_model'),
        ]

    def __str__(self):
        return f"{self.preset_settings_openai} ({self.id})"


class LicenseKey(models.Model):
    """激活码池，由管理员批量生成"""
    code = models.CharField(max_length=40, unique=True, db_index=True, verbose_name="激活码")
    batch_name = models.CharField(max_length=100, blank=True, verbose_name="批次名称")  # 如：双11活动、2025年会员
    days = models.IntegerField(verbose_name="有效天数", help_text="0 = 永久有效，30 = 30天，365 = 1年")

    status = models.SmallIntegerField(
        default=0,
        choices=((0, '未使用'), (1, '已绑定'), (2, '已过期'), (3, '已禁用')),
        verbose_name="状态"
    )
    bound_user = models.ForeignKey(
        'ChatUser',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='bound_licenses',
        verbose_name="绑定用户"
    )
    bound_at = models.DateTimeField(null=True, blank=True, verbose_name="绑定时间")
    expire_at = models.DateTimeField(null=True, blank=True, verbose_name="绝对过期时间")  # 绑定后计算出来

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="生成时间")
    created_by = models.ForeignKey(
        'ChatUser',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='created_licenses',
        verbose_name="生成人"
    )

    class Meta:
        verbose_name = "激活码"
        verbose_name_plural = "激活码管理"

    def __str__(self):
        return self.code


class UserLicense(models.Model):
    """用户实际拥有的授权（业务代码只查这张表）"""
    user = models.OneToOneField(  # 改成 ForeignKey + unique=True 就支持一个用户多个码
        'ChatUser',
        on_delete=models.CASCADE,
        related_name='active_license',
        verbose_name="用户"
    )
    license_key = models.ForeignKey(LicenseKey, on_delete=models.CASCADE, verbose_name="来源激活码")
    start_at = models.DateTimeField(auto_now_add=True, verbose_name="开始时间")
    expire_at = models.DateTimeField(verbose_name="过期时间", help_text="为空表示永久有效")
    is_active = models.BooleanField(default=True, verbose_name="是否当前有效")

    class Meta:
        verbose_name = "用户授权"
        verbose_name_plural = "用户授权列表"

    def __str__(self):
        return f"{self.user.username} → {self.license_key.code}"