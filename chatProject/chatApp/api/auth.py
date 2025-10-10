from rest_framework.authentication import SessionAuthentication

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    全局免 CSRF 的 SessionAuthentication
    """
    def enforce_csrf(self, request):
        return  # 跳过 CSRF 检查
