# utils.py 或者你项目的公共方法文件
from django.conf import settings
from django.utils import timezone
import hashlib
from urllib.parse import quote
import redis
from django_redis import get_redis_connection
import random
from chatApp.models import CharacterCard
# 建立 Redis 连接
redis_client = get_redis_connection('default')


def build_full_image_url(request, uid, character_name):
    """
    获取角色卡片信息，包括 image_name、image_path、tags 和 language。
    逻辑：
    1. 查询 CharacterCard 获取最新记录：
        - 存在记录：返回 image_name、完整 image_path、tags（列表）、language
        - 不存在记录：随机选择默认图片，image_name 空，tags 空，language 'en'

    :param request: 当前 Django request 对象
    :param uid: 角色所属用户 uid
    :param character_name: 角色名
    :return: dict 包含 image_name, image_path, tags, language
    """
    # 默认图片列表（相对路径）
    default_images = [
        "/static/images/default1.png",
        "/static/images/default2.png",
    ]

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
        default_image_relative = random.choice(default_images)
        image_path = request.build_absolute_uri(quote(str(default_image_relative), safe='/'))
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

