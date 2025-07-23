# from django.shortcuts import render, redirect
# from .forms import signup_form
# from .models import ChatUser
# from django.contrib.auth import authenticate, login, logout
# from django.contrib.auth.decorators import login_required
# from django.views.decorators.csrf import csrf_exempt
# from chatApp.models import Room
#
# @csrf_exempt
# @login_required
# def home(request):
#     """首页"""
#     return render(
#         request,
#         "home.html",
#         {
#             "nickname": request.user.nickname,
#             "rooms": Room.objects.all(),
#         },
#     )
#
# @csrf_exempt
# @login_required
# def room_view(request, room_name):
#     chat_room, created = Room.objects.get_or_create(name=room_name)
#     return render(request, 'room.html', {
#         'room': chat_room,
#     })
#
#
# @csrf_exempt
# def user_signup(request):
#     """用户注册"""
#     if request.method == "POST":
#         form_obj = signup_form(request.POST, request.FILES)
#         # 判断校验是否通过
#         if form_obj.is_valid():
#             form_obj.cleaned_data.pop("repassword")
#             user_obj = ChatUser.objects.create_user(
#                 **form_obj.cleaned_data, is_staff=0, is_superuser=0
#             )
#             login(request, user_obj)
#             return redirect("home")
#         else:
#             return render(request, "sign_up.html", {"formobj": form_obj})
#     form_obj = signup_form()
#     return render(request, "sign_up.html", {"formobj": form_obj})
#
#
# @csrf_exempt
# def user_login(request):
#     """用户登录"""
#     if request.method == "POST":
#         username = request.POST["username"]
#         password = request.POST["password"]
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             print("验证成功")
#             login(request, user)
#             return redirect("home")
#         else:
#             print("验证失败")
#     return render(request, "login.html")
#
#
# @csrf_exempt
# def user_logout(request):
#     """用户退出"""
#     logout(request)
#     return redirect("login")