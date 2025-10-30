from google import genai
import json
import os
from dotenv import load_dotenv
import re

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# 新版 SDK 客户端
client = genai.Client(api_key=API_KEY)

def is_nsfw(text: str) -> dict:
    """
    使用 Gemini API 判断文本是否包含 NSFW 内容（成人、暴力、敏感等）。
    若 Gemini 因安全策略拒绝生成内容或返回异常，则自动判定为 NSFW。
    """
    if not text:
        print("⚠️ [NSFW检测] 文本为空，跳过检测。")
        return {"is_nsfw": None, "score": None, "reason": "文本为空"}

    print("🟢 [NSFW检测] 开始检测文本内容（长度:", len(text), "字符）")

    try:
        prompt = (
            "请判断以下文本是否包含 NSFW（成人、暴力、敏感内容，包括但不限于性描写、性暗示、支配与调教、羞辱、暴力等）"
            f"\n文本：{text}\n"
            "返回 JSON 格式：{\"is_nsfw\":true/false,\"score\":0~1,\"reason\":\"…\"}"
        )

        # 调用 Gemini
        print("📡 [NSFW检测] 调用 Gemini API 中 ...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        # 兼容不同字段
        ai_text = getattr(response, "text", None) or getattr(response, "content", None)

        # ✅ 如果 Gemini 拒绝生成内容，则保守判定为 NSFW
        if not ai_text or not isinstance(ai_text, str) or ai_text.strip() == "":
            print("🚫 [NSFW检测] Gemini 拒绝返回结果（可能触发安全过滤） → 判定为 NSFW。")
            return {
                "is_nsfw": True,
                "score": 1.0,
                "reason": "Gemini 拒绝返回结果，可能因文本包含成人/敏感内容，保守判定为 NSFW"
            }

        print("✅ [NSFW检测] Gemini 返回内容，开始解析结果。")

        # 去除 ```json 包裹
        ai_text_clean = re.sub(r"```json|```", "", ai_text).strip()

        try:
            result = json.loads(ai_text_clean)
            print("🧩 [NSFW检测] JSON 解析成功 →", result)
        except Exception:
            print("⚠️ [NSFW检测] JSON 解析失败，原文输出：", ai_text_clean[:200], "...")
            result = {"is_nsfw": None, "score": None, "reason": ai_text_clean}

        return result

    except Exception as e:
        print("💥 [NSFW检测] 调用异常 → 保守判定为 NSFW。错误：", e)
        return {
            "is_nsfw": True,
            "score": 1.0,
            "reason": f"调用异常或安全过滤，保守判定为 NSFW: {e}"
        }
