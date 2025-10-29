import os
from google import generativeai as genai
import json
from dotenv import load_dotenv
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import RoomInfo, CharacterCard ,ForkRelation,Anchor
from chatApp.api.common.common import build_full_image_url,generate_new_room_id, generate_new_room_name
from pymongo import MongoClient
from django.conf import settings
from django.contrib.auth import get_user
import traceback
from django.utils import timezone
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from datetime import datetime
from .api_model.kemini import first_mes_model,current_mes_model
from .fork_format import format_message


# 加载 .env 文件
load_dotenv()

# 配置 Gemini API
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

# 初始化 MongoDB 连接
client = MongoClient(settings.MONGO_URI)
db = client.get_database()

@csrf_exempt
@api_view(['POST'])
def fork_chat(request):
    # 获取用户信息
    user = get_user(request)
    if not user:
        return Response({"success": False, "message": "用户未登录"}, status=401)
    
    user_name = request.session.get('google_name')
    user_id = user.id
    room_id = request.data.get('room_id')
    current_message = request.data.get('message')

    character_card = CharacterCard.objects.filter(room_id=room_id).first()
    character_name = character_card.character_name
    character_date = character_card.character_data
    character_user_name = character_card.username
    character_data_json = json.loads(character_date)

    
    # 获取当前日期时间（或指定日期时间）
    current_date = datetime.now()  # 当前时间
    # 或者指定具体日期时间，例如：
    # current_date = datetime(2025, 9, 30, 17, 51)
    
    # 格式化为 "September 30, 2025 5:51pm"
    formatted_date = current_date.strftime("%B %d, %Y %I:%M%p").replace("AM", "am").replace("PM", "pm")
    
    
    #将数据写入mongodb
    collection = db[room_id]
    collection.insert_one({
        "username": user_name,
        "uid": user_id,
        "character_name": character_name,
        "character_date": "",
        "room_id": room_id,
        "room_name": "",
        "data_type": "user",
        "data": {"name":user_name,"is_user":True,"send_date":formatted_date,"mes":current_message},
        "mes_html": current_message
    })




    # 构造 Gemini API 的 contents
    contents = []

    entries = character_data_json.get("data").get("character_book").get("entries")
    character_description = character_data_json.get("description")
    character_regex_scripts = character_data_json.get("data").get("extensions").get("regex_scripts")
    entrie = ""
    for row in entries:
        entrie += row.get("content")

    first_mes = first_mes_model.replace('{{character_description}}', character_description).replace('{{entrie}}', entrie).replace('{{user}}', character_user_name)
    # contents.append({"text":first_mes})
    contents.append({
        "role": "user",
        "parts": [{"text": first_mes}]
    })

    # 从 MongoDB 查询聊天记录并添加到 contents
    try:

        # chat_records = list(collection.find({}).sort("_id", 1))
        chat_records = list(collection.find({}).sort("_id", -1).limit(10))
        chat_records.reverse()
        
        for item in chat_records:
            data = item.get("data", {})
            is_user = data.get("is_user")
            mes = data.get("mes")

            if not mes or not isinstance(mes, str):
                continue
            role = "user" if is_user  else "model"
            contents.append({
                "role": role,
                "parts": [{"text": mes}]
            })

        current_message = current_mes_model.replace('{{user}}', character_user_name).replace('{{message}}', current_message)
        # 添加用户最新消息
        contents.append({
            "role": "user",
            "parts": [{"text": current_message}]
        })
        # print("**********************8")
        # print(first_mes)
        # print("**********************7")
        # print(current_message)
        # print(contents)
    except Exception as e:
        return Response({
            "code": 1,
            "message": f"获取聊天历史失败: {str(e)}"
        }, status=500)

    # 调用 Gemini API
    try:


        
        


        # system_instruction = {
        #     "parts": parts
        # }


        # 初始化模型
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "candidate_count": 1,
                "temperature": 1.15,
                "top_p": 0.98,
                "top_k": 40,
                "max_output_tokens": 65535,
                "frequency_penalty": 0,
                "presence_penalty": 0,
            },
            safety_settings=[
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, 
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH
                }
            ]
            # system_instruction=system_instruction
        )

        # 调用 generate_content（非流式）
        response = model.generate_content(contents)
        # print("*********")
        # print(response)
        response_text = response.text
        # mes_html = messageFormatting(response_text,character_name,False,False)
        # mes_html = format_message(
        #     mes=response_text,
        #     ch_name=character_name,
        #     isSystem=False,
        #     isUser=False,
        #     messageId=0,
        #     sanitizerOverrides={},
        #     isReasoning=False
        # )
        # print("response_text*")
        # print(response_text)
        mes_html = format_message(
            content=response_text,
            placement=2,  # AI_OUTPUT
            is_markdown=True,
            is_prompt=True,
            is_edit=False,
            depth=0,
            character_regex_scripts=character_regex_scripts
        )
        print("mes_html")
        print(mes_html)
        # 获取当前日期时间（或指定日期时间）
        current_date = datetime.now()  # 当前时间
        # 或者指定具体日期时间，例如：
        # current_date = datetime(2025, 9, 30, 17, 51)
        
        # 格式化为 "September 30, 2025 5:51pm"
        formatted_date = current_date.strftime("%B %d, %Y %I:%M%p").replace("AM", "am").replace("PM", "pm")

        collection.insert_one({
            "username": user_name,
            "uid": user_id,
            "character_name": character_name,
            "character_date": "",
            "room_id": room_id,
            "room_name": "",
            "data_type": "ai",
            "data": {"name":character_name,"is_user":False,"send_date":formatted_date,"mes":response_text},
            "mes_html": mes_html
        })
        return Response({
            "code": 0,
            "message": response_text,
            "html_message": mes_html
        }, status=200)

    except Exception as e:
        return Response({
            "code": 1,
            "message": f"调用 Gemini API 失败: {str(e)}"
        }, status=500)
    





