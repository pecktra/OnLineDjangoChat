# utils.py 或者你项目的公共方法文件
from django.conf import settings
from django.utils import timezone
import hashlib
from urllib.parse import quote
import redis
from django_redis import get_redis_connection
import random
from chatApp.models import CharacterCard
from base64 import b64encode
from urllib import parse
from urllib.parse import urlparse
from collections import OrderedDict
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination
from rest_framework.utils.urls import replace_query_param
import os
# 建立 Redis 连接
redis_client = get_redis_connection('default')


def build_full_image_url(request, uid, character_name):
    """
    获取角色卡片信息，包括 image_name、image_path、tags 和 language。
    逻辑：
    1. 查询 CharacterCard 获取最新记录：
        - 存在记录：返回 image_name、完整 image_path、tags（列表）、language
        - 不存在记录：随机选择默认图片，image_name 空，tags 空，language 'en'
    """
    # 默认图片相对路径
    default_images = [
        "media/headimage/default_image1.png",
        "media/headimage/default_image2.png"
    ]

    # 从 settings 读取站点域名
    site_domain = getattr(settings, "SITE_DOMAIN")

    character_card = CharacterCard.objects.filter(
        uid=uid,
        character_name=character_name
    ).order_by('-create_date').first()

    if character_card:
        image_name = character_card.image_name
        image_path = request.build_absolute_uri(character_card.image_path.url)
        tags = character_card.tags.split(",") if character_card.tags else []
        language = character_card.language or "en"
    else:
        image_name = ""
        # 拼接域名与默认路径
        default_image_relative = random.choice(default_images)
        image_path = f"{site_domain}/{quote(default_image_relative, safe='/')}"
        tags = []
        language = "en"

    return {
        "image_name": image_name,
        "image_path": image_path,
        "tags": tags,
        "language": language
    }


def generate_new_room_id(user_id: str, character_name: str) -> str:
    """
    生成分支的 room_id，按 sha1 前16位
    """
    character_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    room_id = hashlib.sha1(f"Branch_{user_id}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]
    return room_id, character_date

def generate_new_room_name(uid: str, character_name: str) -> str:
    """
    生成生成分支新房间名称，包含 Branch_ + 原房间名 + 角色名 + 时间戳
    """
    timestamp_str = timezone.now().strftime("%Y-%m-%d @%Hh %Mm %Ss %fms")
    return f"Branch_{uid}_{character_name}_{timestamp_str}"


def get_online_room_ids(pattern: str = '*') -> list:
    """
    从 Redis 获取当前在线的房间 room_id 列表

    :param pattern: Redis key 模式，默认匹配所有
    :return: 在线 room_id 列表（字符串）
    """
    try:
        keys = redis_client.keys(pattern)
        # 保留原始逻辑：兼容 Redis 未设置 decode_responses 的情况
        room_ids = [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        return room_ids
    except Exception as e:
        print(f"[Redis Error] 获取在线房间失败: {e}")
        return []


# ======================================================
# ✅ 通用分页类封装（支持 page_size、自定义 ordering、去域名）
# ======================================================

class IDCursorPagination(CursorPagination):
    ordering = '-id'
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        self.request = request
        return super().paginate_queryset(queryset, request, view)

    def get_ordering(self, request, queryset, view):
        if getattr(view, 'ordering', None):
            ordering = view.ordering
        else:
            ordering = self.ordering
        if isinstance(ordering, str):
            return (ordering,)
        return tuple(ordering)

    def encode_cursor(self, cursor):
        """
        生成游标的 Base64 编码。
        """
        tokens = {}
        if cursor.offset != 0:
            tokens['o'] = str(cursor.offset)
        if cursor.reverse:
            tokens['r'] = '1'
        if cursor.position is not None:
            tokens['p'] = cursor.position

        querystring = parse.urlencode(tokens, doseq=True)
        encoded = b64encode(querystring.encode('ascii')).decode('ascii')
        return replace_query_param(self.request.get_full_path(),
                                   self.cursor_query_param, encoded)

    def get_next_link(self):
        if not self.has_next:
            return None
        url = super().get_next_link()
        if not url:
            return None
        parsed = urlparse(url)
        return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path

    def get_previous_link(self):
        if not self.has_previous:
            return None
        url = super().get_previous_link()
        if not url:
            return None
        parsed = urlparse(url)
        return f"{parsed.path}?{parsed.query}" if parsed.query else parsed.path

    def get_paginated_response(self, data):
        """
        最终返回结构中添加 code/data 外层包装
        """
        pagination_data = OrderedDict([
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ])
        return Response({
            "code": 0,
            "data": pagination_data
        })


