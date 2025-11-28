from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.conf import settings
from pymongo import MongoClient
from chatApp.models import CharacterCard, Anchor, RoomImageBinding
import json
import hashlib
import os
import re

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.chat_db


@api_view(['POST'])
def import_card(request):
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'status': 'error', 'message': '缺少图片文件'}, status=400)

        image_file = request.FILES['image']
        character_data_str = request.POST.get('character_data', '{}')
        username = request.POST.get('username', '')
        filename = request.POST.get('filename', '')

        # 解析 JSON 数据
        try:
            character_json = json.loads(character_data_str)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': '无效的JSON数据'}, status=400)

        data = character_json.get('data', {})
        character_name = data.get('name', '')
        create_date = character_json.get('create_date', '')

        # 查找 uid
        user = Anchor.objects.filter(handle=username).first()
        if not user:
            return JsonResponse({'status': 'error', 'message': "not found username"}, status=500)

        room_id = hashlib.sha1(f"{user.uid}_{character_name}_{create_date}".encode('utf-8')).hexdigest()[:16]

        # 检查是否重复上传
        if CharacterCard.objects.filter(image_name=filename, username=username).exists():
            existing_card = CharacterCard.objects.get(image_name=filename, username=username)
            return JsonResponse({
                'status': 'success',
                'message': '卡不可重复上传',
                'data': {
                    'id': existing_card.id,
                    'image_path': existing_card.image_path.url,
                    'full_path': request.build_absolute_uri(existing_card.image_path.url)
                }
            })

        # 处理 tags
        tags_list = character_json.get('tags', [])
        if not isinstance(tags_list, list):
            tags_list = []

        tags = ",".join(tags_list) if tags_list else None

        # 创建数据库记录
        character_card = CharacterCard.objects.create(
            uid=user.uid,
            username=username,
            character_name=character_name,
            image_name=filename,
            character_data=json.dumps(character_json, ensure_ascii=False),
            create_date=create_date,
            language="cn" if re.search(r'[\u4e00-\u9fff]', character_name) else "en",
            tags=tags
        )

        # 保存图片文件
        sub_path = os.path.join(username, 'characters', f"{filename}.png")
        full_path = os.path.join(settings.MEDIA_ROOT, sub_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'wb') as f:
            for chunk in image_file.chunks():
                f.write(chunk)

        character_card.image_path.name = sub_path
        character_card.save()


        return JsonResponse({
            'status': 'success',
            'message': '上传成功，已标记为不可见',
            'data': {
                'id': character_card.id,
                'image_path': character_card.image_path.url,
                'full_path': request.build_absolute_uri(character_card.image_path.url)
            }
        })

    except Exception as e:
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
