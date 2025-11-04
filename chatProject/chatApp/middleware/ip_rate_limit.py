import time
from django.http import JsonResponse

VISIT_RECORD = {}  # 全局内存记录

class IpRateLimitMiddleware:
    """
    简单基于内存的 IP 限流中间件
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.TIME_WINDOW = 60  # 秒
        self.MAX_REQUESTS = 15  # 时间窗口内最大请求数

    def __call__(self, request):
        ip = self.get_client_ip(request)
        now = time.time()
        record = VISIT_RECORD.get(ip, [])

        # 清理过期请求
        record = [t for t in record if now - t < self.TIME_WINDOW]
        record.append(now)
        VISIT_RECORD[ip] = record

        if len(record) > self.MAX_REQUESTS:
            return JsonResponse({"status": "error", "message": "请求过于频繁"}, status=429)

        return self.get_response(request)

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
