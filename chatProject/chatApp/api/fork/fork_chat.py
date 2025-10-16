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
        "character_date": character_date,
        "room_id": room_id,
        "room_name": "",
        "data_type": "user",
        "data": {"name":user_name,"is_user":True,"send_date":formatted_date,"mes":current_message},
        "mes_html": current_message
    })




    # 构造 Gemini API 的 contents
    contents = []

    # 从 MongoDB 查询聊天记录并添加到 contents
    try:

        chat_records = list(collection.find({}).sort("_id", 1))

        for item in chat_records:
            data = item.get("data", {})
            is_user = data.get("is_user")
            mes = data.get("mes")
            if not mes or not isinstance(mes, str):
                continue
            role = "model" if is_user == "false" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": mes}]
            })

        # 添加用户最新消息
        contents.append({
            "role": "user",
            "parts": [{"text": current_message}]
        })


    except Exception as e:
        return Response({
            "code": 1,
            "message": f"获取聊天历史失败: {str(e)}"
        }, status=500)

    # 调用 Gemini API
    try:
        # 定义 system_instruction
        # system_instruction = {
        #     "parts": []
        # }
#         system_instruction = {
#             "parts": [
#                 {
#                     "text": "Write 金庸群侠传之武林高手's next reply in a fictional chat between 金庸群侠传之武林高手 and pride88."
#                 },
#                 {
#                     "text": "金庸群侠传之武林高手不是一个角色，是武侠世界的描述者，小说的创作者。"
#                 },
#                 {
#                     "text": """
# <StatusBlockRule>
# The status bar must appear at the end of each reply. The status bar must have "<StatusBlock>" at the beginning and end and must strictly follow the following example:

# <StatusBlock>
# 气血：{{char.hp_status}}
# 神识：{{char.awareness_status}}
# 因果：{{char.relationship_status}}
# 声望：{{char.reputation_status}}
# 招式：{{char.skill_status}}
# 心法：{{char.internal_art_status}}
# 身法：{{char.movement_status}}
# 奇技：{{char.special_tech_status}}
# 当前地点：{{char.current_location}}
# 行囊物品：{{char.inventory_list}}
# 当前摘要：{{char.current_summary}}
# 选项1：{{char.option1_text}}
# 选项2：{{char.option2_text}}
# 选项3：{{char.option3_text}}
# 时间：{{嘉庆XX年X月X日酉时}}
# 人名：{{Current.NPC1}}
# 服装：{{Current.Clothing}}
# 动作：{{Current.Behavir}}
# 人名：{{Current.NPC2}}
# 服装：{{Current.Clothing}}
# 动作：{{Current.Behavir}}
# 人名：{{Current.NPC3}}
# 服装：{{Current.Clothing}}
# 动作：{{Current.Behavir}}
# </StatusBlock>

# <!-重要提示: {{}}中的内容是变量,ai应根据情况填写,不可直接输出{{}}.在 <物品> 标签内，请将所有物品用英文逗号 `,` 连接，不要在逗号前后添加空格，例如：木剑,硬面饼,止血草.未知数值请用 '-' 代替.npc栏位仅展示正在出场的重要npc,最多3人.-!>
# </StatusBlockRule>
# """
#                 },
#                 {
#                     "text": "[Start a new Chat]"
#                 }
#             ]
#         }
        # 初始化模型
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config={
                "temperature": 1,
                "top_p": 1,
                "max_output_tokens": 40000,
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
        response_text = response.text
        mes_html = message_formatting(response_text,character_name,False,False)


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
            "character_date": character_date,
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
    







from typing import Optional

def message_formatting(
    mes: str,
    ch_name: str,
    is_system: bool,
    is_user: bool,

    sanitizer_overrides: Optional[dict] = None,
    is_reasoning: bool = False
) -> str:
    """
    简化版消息格式化函数
    
    Args:
        mes: 消息文本
        ch_name: 角色名称
        is_system: 是否为系统消息
        is_user: 是否为用户消息

        sanitizer_overrides: HTML净化器选项覆盖
        is_reasoning: 是否为推理输出
        
    Returns:
        格式化的HTML字符串
    """
    if not mes:
        return ''
    
    if sanitizer_overrides is None:
        sanitizer_overrides = {}
    
    processed_message = mes
    

    
    # 特殊角色处理
    if ch_name == "COMMENT" and is_system and not is_user:
        is_system = False
    
    # 系统消息的特殊处理
    if is_system and ch_name != "system":  # 替换实际的系统用户名
        is_system = False
    
    # 提示偏置处理（简化）
    # 如果有用户提示偏置且不显示，则从消息开头移除
    user_prompt_bias = ""  # 这里可以设置实际的提示偏置
    show_user_prompt_bias = True  # 这里可以设置实际的显示设置
    
    if not show_user_prompt_bias and ch_name and not is_user and not is_system and user_prompt_bias and processed_message.startswith(user_prompt_bias):
        processed_message = processed_message[len(user_prompt_bias):]
    
    # 非系统消息的基本处理
    if not is_system:
        # HTML标签编码（可选）
        encode_tags = True  # 这里可以设置实际的编码设置
        if encode_tags:
            processed_message = processed_message.replace('<', '&lt;').replace('>', '&gt;')
        
        # 推理字符串处理
        reasoning_prefix = ""  # 这里可以设置实际的推理前缀
        reasoning_suffix = ""  # 这里可以设置实际的推理后缀
        
        reasoning_strings = [reasoning_prefix, reasoning_suffix]
        for reasoning_string in reasoning_strings:
            if reasoning_string and reasoning_string.strip() and reasoning_string in processed_message:
                # 只替换第一个出现的推理字符串
                processed_message = processed_message.replace(reasoning_string, escape_html(reasoning_string), 1)
        
        # 引号处理（简化版）
        processed_message = process_quotes(processed_message)
        
        # LaTeX数学公式简化处理
        processed_message = processed_message.replace('\\begin{align*}', '$$')
        processed_message = processed_message.replace('\\end{align*}', '$$')
        
        # 简单的Markdown处理
        processed_message = simple_markdown_to_html(processed_message)
        
        # 代码块处理
        processed_message = process_code_blocks(processed_message)
    
    # 移除角色名称（如果设置不允许显示）
    allow_name_display = True  # 这里可以设置实际的显示设置
    if not allow_name_display and ch_name and not is_user and not is_system:
        # 移除消息开头的角色名称
        if processed_message.startswith(f"{ch_name}:"):
            processed_message = processed_message[len(f"{ch_name}:"):].lstrip()
        # 移除换行后的角色名称
        processed_message = processed_message.replace(f"\n{ch_name}:", "\n")
    
    # HTML净化（简化）
    processed_message = simple_sanitize_html(processed_message, sanitizer_overrides)
    
    return processed_message

def escape_html(text: str) -> str:
    """简单的HTML转义"""
    return (text.replace('&', '&amp;')
               .replace('<', '&lt;')
               .replace('>', '&gt;')
               .replace('"', '&quot;')
               .replace("'", '&#039;'))

def process_quotes(text: str) -> str:
    """处理引号"""
    # 简单的英文双引号处理
    import re
    text = re.sub(r'"([^"]*)"', r'<q>"\1"</q>', text)
    return text

def simple_markdown_to_html(text: str) -> str:
    """简单的Markdown到HTML转换"""
    # 粗体
    text = text.replace('**', '<strong>', 1)
    text = text.replace('**', '</strong>', 1)
    
    # 斜体
    text = text.replace('*', '<em>', 1)
    text = text.replace('*', '</em>', 1)
    
    # 代码
    text = text.replace('`', '<code>', 1)
    text = text.replace('`', '</code>', 1)
    
    # 换行
    text = text.replace('\n', '<br>')
    
    return text

def process_code_blocks(text: str) -> str:
    """处理代码块"""
    import re
    
    # 处理多行代码块
    def replace_code_blocks(match):
        code_content = match.group(1)
        return f'<pre><code>{code_content}</code></pre>'
    
    text = re.sub(r'```(?:\w+)?\n(.*?)\n```', replace_code_blocks, text, flags=re.DOTALL)
    
    # 处理内联代码
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    return text

def simple_sanitize_html(html_content: str, config: dict = None) -> str:
    """
    简单的HTML净化
    """
    if config is None:
        config = {}
    
    # 允许的基本HTML标签
    allowed_tags = {
        'br', 'strong', 'em', 'code', 'pre', 'q', 
        'p', 'div', 'span', 'b', 'i', 'u'
    }
    
    # 简单的标签过滤
    import re
    
    def sanitize_tag(match):
        tag = match.group(1)
        if tag.lower() in allowed_tags:
            return match.group(0)  # 保留允许的标签
        else:
            return escape_html(match.group(0))  # 转义不允许的标签
    
    # 过滤标签
    html_content = re.sub(r'</?([a-zA-Z][a-zA-Z0-9]*)[^>]*>', sanitize_tag, html_content)
    
    return html_content
