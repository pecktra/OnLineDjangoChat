# utils.py 或者你项目的公共方法文件
from django.conf import settings
from django.utils import timezone
import hashlib
from urllib.parse import quote
import redis
from django_redis import get_redis_connection

# 建立 Redis 连接
redis_client = get_redis_connection('default')


def build_full_image_url(request, relative_path: str) -> str:
    """
    拼接图片完整 URL

    :param request: 当前 Django request 对象
    :param relative_path: 图片相对路径，比如 /characters/哈利波特的魔法世界.png
    :return: 完整 URL，例如 https://example.com/media/characters/哈利波特的魔法世界.png
    """
    if not relative_path:
        return ""

    # 如果传入的路径不是以 /media/ 开头，加上 MEDIA_URL
    if not relative_path.startswith(settings.MEDIA_URL):
        relative_path = f"{settings.MEDIA_URL}{relative_path.lstrip('/')}"

    # 使用 build_absolute_uri 拼接域名
    return request.build_absolute_uri(relative_path)


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