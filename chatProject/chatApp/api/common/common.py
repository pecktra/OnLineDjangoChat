# utils.py 或者你项目的公共方法文件
from django.conf import settings
from django.utils import timezone
import hashlib
from urllib.parse import quote
import redis
from django_redis import get_redis_connection
import random
from chatApp.models import CharacterCard,RoomImageBinding
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


def build_full_image_url(request, uid, room_id, search_tag=None):
    """
    返回值永远是 dict
    - 匹配用字符串，返回给前端用数组
    """

    default_images = ["headimage/default_image1.png", "headimage/default_image2.png"]
    site_domain = getattr(settings, "SITE_DOMAIN", "")

    binding = RoomImageBinding.objects.filter(uid=uid, room_id=room_id).first()

    image_name = ""
    tags_str = ""
    language = "en"
    default_path = random.choice(default_images)
    image_path = f"{site_domain}/media/{quote(default_path, safe='/')}"

    if binding and binding.image_id:
        card = CharacterCard.objects.filter(id=binding.image_id)\
            .values('image_name', 'image_path', 'tags', 'language')\
            .first()
        if card:
            image_name = card['image_name']
            tags_str = card['tags'] or ""  # 用于匹配
            language = card['language']
            image_path = f"{site_domain}/media/{quote(card['image_path'], safe='/')}"

    # 构造前端返回数组
    tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]

    full_info = {
        "image_name": image_name,
        "image_path": image_path,
        "tags": tags_list,  # 返回数组
        "language": language.upper() if language in ('en', 'cn') else language
    }

    # search_tag 为空 → 直接返回
    if not search_tag or str(search_tag).strip() == "":
        return full_info

    # 模糊匹配
    search_tag = search_tag.strip().lower()
    if search_tag in ("en", "cn"):
        match = (language == search_tag)
    else:
        match = search_tag in tags_str.lower()  # 匹配用原始字符串

    # 不匹配 → 返回空图
    if not match:
        empty_path = f"{site_domain}/media/{quote(random.choice(default_images), safe='/')}"
        empty_info = {
            "image_name": "",
            "image_path": empty_path,
            "tags": [],  # 空数组
            "language": "en"
        }
        return empty_info

    return full_info

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


