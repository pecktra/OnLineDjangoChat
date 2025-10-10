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
