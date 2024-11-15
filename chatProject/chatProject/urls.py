"""
URL configuration for chatProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from chatApp.views import home,user_login,user_signup,user_logout

# 导入静态文件模块，为了显示上传图片
from django.conf.urls.static import static
from . import settings
from chatApp import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'), # 首页
    path('login/', user_login, name='login'), # 登录
    path('signup/', user_signup, name='signup'), # 注册
    path('logout/', user_logout, name='logout'), # 退出
    path('chat/<str:room_name>/', views.room_view, name='chatroom'), # 聊天室
]

urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)