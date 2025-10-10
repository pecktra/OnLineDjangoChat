# utils.py 或者你项目的公共方法文件
from django.conf import settings

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
    生成新的 room_id，按 sha1 前16位
    """
    character_date = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    room_id = hashlib.sha1(f"Branch_{user_id}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]
    return room_id, character_date

def generate_new_room_name(origin_room_name: str, character_name: str) -> str:
    """
    生成新房间名称，包含 Branch_ + 原房间名 + 角色名 + 时间戳
    """
    timestamp_str = timezone.now().strftime("%Y-%m-%d @%Hh %Mm %Ss %fms")
    return f"Branch_{origin_room_name}_{character_name}_{timestamp_str}"