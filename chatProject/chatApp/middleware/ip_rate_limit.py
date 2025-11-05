import time
from django.http import JsonResponse
from django.utils import timezone
from collections import defaultdict
from chatApp.models import IPBlacklist  # 替换为你的实际路径

# 单 IP 单接口访问记录
VISIT_RECORD_60S = defaultdict(list)  # 60s 限流
VISIT_RECORD_10S = defaultdict(list)  # 10s 黑名单检测


class IpRateLimitMiddleware:
    """
    单接口访问限流 + 黑名单
    """

    # 限流参数
    TIME_WINDOW_LIMIT = 60      # 秒
    MAX_REQUESTS_LIMIT = 200    # 60秒内最多访问次数

    BLACKLIST_WINDOW = 10       # 秒
    MAX_REQUESTS_BLACKLIST = 30 # 10秒内超过该次数拉黑

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self.get_client_ip(request)
        path = request.path
        now = time.time()

        # 1️⃣ 检查黑名单
        if IPBlacklist.objects.filter(ip=ip, is_active=True).exists():
            return JsonResponse({
                "status": "error",
                "message": "您的IP已被封禁，禁止访问。"
            }, status=403)

        # 2️⃣ 60s 限流逻辑
        key_60s = (ip, path)
        record_60s = VISIT_RECORD_60S[key_60s]
        record_60s = [t for t in record_60s if now - t < self.TIME_WINDOW_LIMIT]
        record_60s.append(now)
        VISIT_RECORD_60S[key_60s] = record_60s

        if len(record_60s) > self.MAX_REQUESTS_LIMIT:
            return JsonResponse({"status": "error", "message": "请求过于频繁"}, status=429)

        # 3️⃣ 10s 黑名单检测逻辑
        key_10s = (ip, path)
        record_10s = VISIT_RECORD_10S[key_10s]
        record_10s = [t for t in record_10s if now - t < self.BLACKLIST_WINDOW]
        record_10s.append(now)
        VISIT_RECORD_10S[key_10s] = record_10s

        if len(record_10s) > self.MAX_REQUESTS_BLACKLIST:
            self.add_to_blacklist(ip, path)
            return JsonResponse({
                "status": "error",
                "message": "检测到异常访问行为，您的IP已被永久封禁。"
            }, status=403)

        return self.get_response(request)

    def add_to_blacklist(self, ip, path):
        """写入数据库黑名单"""
        IPBlacklist.objects.update_or_create(
            ip=ip,
            defaults={
                "path": path,
                "reason": f"接口 {path} 10秒内访问超过 {self.MAX_REQUESTS_BLACKLIST} 次",
                "is_active": True,
                "created_at": timezone.now()
            }
        )
        print(f"[BLACKLIST] IP {ip} 已被封禁，接口 {path}")

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
