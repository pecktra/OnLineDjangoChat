import os
from google import generativeai as genai
import json
from dotenv import load_dotenv
import re

# 加载 .env 文件（如果有）
load_dotenv()

# 直接从环境变量读取 GEMINI_API_KEY
API_KEY = os.getenv("GEMINI_API_KEY")

# 初始化 Gemini API
genai.configure(api_key=API_KEY)

def is_nsfw(text: str) -> dict:
    """
    判断文本是否 NSFW
    参数：
        text: str 要检测的文本
    返回：
        dict {
            "is_nsfw": True/False/None,
            "score": 0~1 或 None,
            "reason": 简短解释或 AI 原文
        }
    """
    print(text)
    if not text:
        return {"is_nsfw": None, "score": None, "reason": "文本为空"}

    try:
        prompt = f"""请判断以下文本是否包含 NSFW（成人、暴力、敏感内容，包括但不限于性描写、性暗示、支配与调教、羞辱、暴力、或任何可能令人不适的内容）。特别注意中文文本中的隐晦表达，如‘抖M’、‘调教’、‘肉棒’、‘足交’、‘羞辱’、‘排泄’等，以及描述性行为、支配场景或身体部位的语境。返回 JSON 格式：
{{
  "is_nsfw": true/false,
  "score": 0~1,
  "reason": "简短解释，说明检测到的具体 NSFW 内容或无 NSFW 的原因"
}}

文本：{text[:1000]}"""  # 限制长度以避免 API 超限
        chat = genai.Chat.create(model="gemini-2.5-flash")
        response = chat.send_message(prompt)

        try:
            result = json.loads(response.text)
        except:
            result = {"is_nsfw": None, "score": None, "reason": response.text}

        return result

    except Exception as e:
        return {"is_nsfw": None, "score": None, "reason": str(e)}


# 1. NSFW 关键词列表，可随时扩展
NSFW_KEYWORDS = [
    "阴茎", "乳头", "小穴", "后庭",
     "淫乱",
    "性交",  "裸舞", "乳房", "私处",
    "性行为", "性器官", "诱奸", "猥亵", "性虐",
    "性幻想", "性冲动", "调情",
    "做爱", "口交", "肛交", "乳交", "性服务",
    "色情图片", "成人片", "骚扰", "裸身",
    "露点", "性交影片", "性录像", "性交易", "淫秽",
    "性诱惑", "性游戏", "性虐待", "恋足",
    "性奴", "性癖", "淫欲"
]

# 2. 编译正则（忽略大小写）
NSFW_PATTERN = re.compile("|".join(map(re.escape, NSFW_KEYWORDS)), flags=re.IGNORECASE)


def is_nsfw_text(text: str) -> dict:
    """
    判断文本是否包含 NSFW 关键词
    """
    if not text or not text.strip():
        return {"is_nsfw": None, "score": None, "reason": "文本为空"}

    # 去掉空白字符再匹配
    text_clean = re.sub(r"\s+", "", text)
    if NSFW_PATTERN.search(text_clean):
        return {"is_nsfw": True, "score": 1.0, "reason": "包含 NSFW 关键词"}
    else:
        return {"is_nsfw": False, "score": 0.0, "reason": "未检测到 NSFW 内容"}


def check_nsfw_in_character_data(character_json: dict) -> dict:
    """
    递归检测 character_json['data'] 中所有字符串字段
    """
    data = character_json.get('data', {})

    def _check(obj):
        if isinstance(obj, str) and obj.strip():
            return is_nsfw_text(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                result = _check(v)
                if result.get("is_nsfw"):
                    return result
        elif isinstance(obj, list):
            for item in obj:
                result = _check(item)
                if result.get("is_nsfw"):
                    return result
        return {"is_nsfw": False, "score": 0.0, "reason": "未检测到 NSFW 内容"}

    return _check(data)