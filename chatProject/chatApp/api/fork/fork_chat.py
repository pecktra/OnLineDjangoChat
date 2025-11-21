import os
from google import generativeai as genai
import json
from dotenv import load_dotenv
import re
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from chatApp.models import Preset, CharacterCard,ForkTrace
from chatApp.api.common.common import build_full_image_url,generate_new_room_id, generate_new_room_name
from pymongo import MongoClient
from django.conf import settings
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
import traceback
from django.utils import timezone
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from datetime import datetime
from .api_model.kemini import first_mes_model,current_mes_model
from .fork_format import format_message
from dateutil import parser
import hashlib


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
@permission_classes([IsAuthenticated])
def fork_chat(request):
    # 获取用户信息
    user = request.user
    if not user:
        return Response({"success": False, "message": "用户未登录"}, status=401)

    user_name = user.username
    user_id = user.id
    room_id = request.data.get('room_id')



    fork_room_info = ForkTrace.objects.filter(current_room_id=room_id).first()
    source_room_id = fork_room_info.source_room_id


    current_message = request.data.get('message')

    character_card = CharacterCard.objects.filter(room_id=source_room_id).first()

    character_name = character_card.character_name
    character_date = character_card.character_data
    character_user_name = character_card.username
    character_data_json = json.loads(character_date)


    # room_id = hashlib.sha1(f"{user_id}_{character_name}_{character_date}".encode('utf-8')).hexdigest()[:16]


    # 获取当前日期时间（或指定日期时间）
    current_date = datetime.now()  # 当前时间
    # 或者指定具体日期时间，例如：
    # current_date = datetime(2025, 9, 30, 17, 51)

    # 格式化为 "September 30, 2025 5:51pm"
    formatted_date = current_date.strftime("%B %d, %Y %I:%M%p").replace("AM", "am").replace("PM", "pm")

    #将数据写入mongodb
    collection = db[room_id]
    floor_user = collection.count_documents({}) + 1
    collection.insert_one({
        "username": user_name,
        "uid": user_id,
        "character_name": character_name,
        "character_date": "",
        "room_id": room_id,
        "room_name": "",
        "data_type": "user",
        "data": {"name":user_name,"is_user":True,"send_date":formatted_date,"mes":current_message},
        "mes_html": current_message,
        "floor": floor_user
    })











    # 构造 Gemini API 的 chat history contents
    chat_history_contents = []
    entrie = ""
    character_regex_scripts = ""
    character_book = character_data_json.get("data").get("character_book","")

    if character_book:
        entries = character_book.get("entries","")
        if entries:
            for row in entries:
                entrie += row.get("content")
    character_description = character_data_json.get("description","")
    extensions = character_data_json.get("data").get("extensions","")
    if extensions:
        character_regex_scripts = extensions.get("regex_scripts")





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
            chat_history_contents.append({
                "role": role,
                "parts": [{"text": mes}]
            })



    except Exception as e:
        return Response({
            "code": 1,
            "message": f"获取聊天历史失败: {str(e)}"
        }, status=500)




    # 预设处理，没有则使用默认预设

    candidate_count= 1
    temperature= 1.15
    top_p= 0.98
    top_k= 40
    max_output_tokens= 65535
    frequency_penalty= 0
    presence_penalty= 0

    contents = []
    #获取当前房间的预设
    preset_info = Preset.objects.filter(room_id=source_room_id).first()
    #已经保存了预设
    if preset_info:
        preset_settings_openai = preset_info.preset_settings_openai
        temperature            = preset_info.temp_openai
        top_k           = preset_info.top_k_openai
        top_p           = preset_info.top_p_openai
        openai_max_context     = preset_info.openai_max_context
        max_output_tokens      = preset_info.openai_max_tokens
        google_model           = preset_info.google_model
        model_n                = preset_info.model_n
        preset_json            = preset_info.preset_json

        preset_json_list = json.loads(preset_json)
        for data in preset_json_list:
            identifier = data.get("identifier","")
            content = data.get("content","")

            content = content.replace('{{character_description}}', character_description).replace('{{entrie}}', entrie).replace('{{user}}', character_user_name).replace('{{lastUserMessage}}', current_message)
            if identifier != "chatHistory":
                contents.append({
                "role": data.get("role","user"),
                "parts": [{"text":content }]
                })
            else:
                #合并历史聊天内容
                contents.extend(chat_history_contents)
    #未保存预设
    else:

        first_mes = first_mes_model.replace('{{character_description}}', character_description).replace('{{entrie}}', entrie).replace('{{user}}', character_user_name)
        # contents.append({"text":first_mes})
        contents.append({
            "role": "user",
            "parts": [{"text": first_mes}]
        })
        #合并历史聊天内容
        contents.extend(chat_history_contents)

        current_message = current_mes_model.replace('{{user}}', character_user_name).replace('{{message}}', current_message)
        # 添加用户最新消息
        contents.append({
            "role": "user",
            "parts": [{"text": current_message}]
        })



    #合并contents
    contents_final = []
    for row in contents:
            role = row.get("role")
            if role in('system','tool'):
                role = "user"
            elif role == "assistant":
                role = "model"
            if role:

                if len(contents_final) >0 and role == contents_final[-1].get("role"):
                    # 拼接内容
                    current_content = row.get("parts")[0].get("text")
                    existing_content = contents_final[-1].get("parts")[0].get("text")
                    contents_final[-1]["parts"] =[{"text":  existing_content + "\n\n" + current_content}]
                else:
                    contents_final.append({
                        "role": role,
                        "parts": [{"text": row.get("parts")[0].get("text")}]
                    });



    # 调用 Gemini API
    try:
        # 初始化模型
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config={
                "candidate_count": 1,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_output_tokens": max_output_tokens,
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
        response = model.generate_content(contents_final)
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
        # print("mes_html")
        # print(mes_html)

        # 获取当前日期时间（或指定日期时间）
        current_date = datetime.now()  # 当前时间
        # 或者指定具体日期时间，例如：
        # current_date = datetime(2025, 9, 30, 17, 51)

        # 格式化为 "September 30, 2025 5:51pm"
        formatted_date = current_date.strftime("%B %d, %Y %I:%M%p").replace("AM", "am").replace("PM", "pm")

        floor_ai = collection.count_documents({}) + 1

        collection.insert_one({
            "username": user_name,
            "uid": user_id,
            "character_name": character_name,
            "character_date": "",
            "room_id": room_id,
            "room_name": "",
            "data_type": "ai",
            "data": {"name":character_name,"is_user":False,"send_date":formatted_date,"mes":response_text},
            "mes_html": mes_html,
            "floor": floor_ai
        })
        # ------------------ 返回结果 ------------------
        result = []

        # 从 MongoDB 查询最新的两条聊天记录，按插入顺序排列
        chat_records = list(collection.find({}).sort("_id", -1).limit(2))  # 获取最新的2条消息
        chat_records.reverse()  # 反转顺序，使得最新的消息在前

        # 遍历聊天记录，只返回 'user' 或 'ai' 类型的消息
        for item in chat_records:
            data = item.get("data", {})
            data_type = item.get("data_type")  # 获取消息类型（user 或 ai）

            # 只返回 'user' 或 'ai' 类型的消息
            if data_type not in ['user', 'ai']:
                continue

            send_date =  timezone.now().isoformat() + 'Z'


            filtered_data = {
                "name": data.get("name"),
                "is_user": data.get("is_user"),
                "send_date": send_date,
                "mes": data.get("mes")
            }

            # 添加消息到结果
            result.append({
                "floor": item.get("floor", 0),
                "data_type": data_type,  # 'user' 或 'ai'
                "data": filtered_data,
                "mes_html": item.get("mes_html", "")
            })

        return Response({
            "code": 0,
            "message": "success",
            "data": result
        }, status=200)


    except Exception as e:
        return Response({
            "code": 1,
            "message": f"调用 Gemini API 失败: {str(e)}"
        }, status=500)






