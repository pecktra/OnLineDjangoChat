import os
from google import generativeai as genai
import json
from dotenv import load_dotenv
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import Preset
from chatApp.api.common.common import build_full_image_url,generate_new_room_id, generate_new_room_name
from pymongo import MongoClient
from django.conf import settings
from django.contrib.auth import get_user
import traceback
from django.utils import timezone
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from datetime import datetime
import hashlib



@csrf_exempt
@api_view(['POST'])
def preset_save(request):
    # 获取用户信息
    print("来了preset_save")
    data = json.loads(request.body)
    uid = data.get('uid',"")
    character_name = data.get('character_name',"")
    character_date = data.get('character_date',"")

    room_id = hashlib.sha1(f"{uid}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]
    print("preset_save")
    print(room_id)


    oai_settings =data.get('oai_settings')
    preset_settings_openai = oai_settings.get('preset_settings_openai',"")

    temp_openai =oai_settings.get('temp_openai',"")
    top_p_openai =oai_settings.get('top_p_openai',"")
    top_k_openai =oai_settings.get('top_k_openai',"")
    openai_max_context =oai_settings.get('openai_max_context',"")
    openai_max_tokens =oai_settings.get('openai_max_tokens',"")
    google_model =oai_settings.get('google_model',"")
    n =oai_settings.get('n',"")

    prompts = oai_settings.get("prompts","")
    prompt_map = {item['identifier']: item for item in prompts}
    prompt_order = oai_settings.get("prompt_order","")
    prompts_final = []

    for orders in prompt_order:
        for order in orders.get("order",""):

            identifier = order.get("identifier","")
            enabled = order.get("enabled","")
            if enabled:
                prompt =  prompt_map.get(identifier)
                name = prompt.get("name","")
                role = prompt.get("role","")
                content = prompt.get("content","")
                marker = prompt.get("marker","")
                system_prompt = prompt.get("system_prompt","")
                injection_position = prompt.get("injection_position",None)
                dic = {
                    "identifier":identifier,
                    "name":name,
                    "role":role,
                    "content":content,
                    "marker":marker,
                    "system_prompt":system_prompt,
                    "injection_position":injection_position
                }
                prompts_final.append(dic)


    print("来了")
    # 创建房间记录
    preset_info, created = Preset.objects.update_or_create(
        room_id=room_id,  # 根据room_id查找，如果存在就更新
        defaults={
            'preset_settings_openai': preset_settings_openai,
            'temp_openai': temp_openai,
            'top_k_openai': top_k_openai,
            'top_p_openai': top_p_openai,
            'openai_max_context': openai_max_context,
            'openai_max_tokens': openai_max_tokens,
            'google_model': google_model,
            'model_n': n,
            'preset_json': json.dumps(prompts_final, ensure_ascii=False)
        }
    )




    return Response({
        "code": 0
    }, status=200)




