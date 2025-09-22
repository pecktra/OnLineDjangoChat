from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from pymongo import MongoClient

from django.http import JsonResponse
from chatApp.models import CharacterCard,Anchor
import json
import os
import hashlib
import re  # 用于检测中文
# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.chat_db  # 连接到 chat_db 数据库


@api_view(['POST'])
def import_card(request):
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': '缺少图片文件'}, status=400)

        image_file = request.FILES['image']
        character_data_str = request.POST.get('character_data', '{}')
        username = request.POST.get('username', '')
        filename = request.POST.get('filename', '')

        # 解析JSON数据
        try:
            character_json = json.loads(character_data_str)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '无效的JSON数据'}, status=400)

        character_name = character_json['data']['name']
        create_date = character_json['create_date']

        # 1. 手动创建用户目录
        user_dir = os.path.join(settings.MEDIA_ROOT, username, 'characters')
        os.makedirs(user_dir, exist_ok=True)

        # 构建完整文件路径
        file_path = os.path.join(user_dir, filename + ".png")
        relative_path = f'{username}/characters/{filename}.png'

        # 判断是否创建过
        if CharacterCard.objects.filter(image_path=relative_path).exists():
            return JsonResponse({'status': 'success', 'message': '卡不可重复上传'})

        # 手动保存图片文件
        with open(file_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        # 查找uid
        user = Anchor.objects.filter(handle=username).first()
        if not user:
            return JsonResponse({'status': 'error', 'message': "not found username"}, status=500)

        room_id = hashlib.sha1(f"{user.uid}_{character_name}_{create_date}".encode('utf-8')).hexdigest()[:16]

        # 自动判断语言：如果有中文字符则设为 cn，否则 en
        language = "cn" if re.search(r'[\u4e00-\u9fff]', character_name) else "en"

        # 处理 tags
        tags_list = character_json.get('tags', [])
        if isinstance(tags_list, list) and tags_list:
            tags = ",".join(tags_list)
        else:
            tags = None

        # 自动判断是否私密卡：只要 tags 里有 NSFW 相关关键字
        nsfw_keywords = {"Not Safe for Work", "NotSafeforWork", "NSFW", "nsfw"}
        is_private = any(tag.strip() in nsfw_keywords for tag in tags_list)

        # 创建数据库记录
        character_card = CharacterCard.objects.create(
            room_id=room_id,
            uid=user.uid,
            username=username,
            character_name=character_name,
            image_name=filename,
            image_path=relative_path,
            character_data=character_json,
            create_date=create_date,
            language=language,
            tags=tags,
            is_private=is_private
        )

        return JsonResponse({
            'status': 'success',
            'message': '上传成功',
            'data': {
                'id': character_card.id,
                'image_path': character_card.image_path,
                'full_path': os.path.join(settings.MEDIA_URL, relative_path)
            }
        })

    except Exception as e:
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)










