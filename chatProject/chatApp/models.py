from django.db import models
from django.contrib.auth.models import AbstractUser


class ChatUser(AbstractUser):
    '''聊天用户模型'''
    nickname = models.CharField(max_length=32, verbose_name="昵称", blank=True)
    phone = models.CharField(
        max_length=11, null=True, verbose_name="手机号"
    )
    img = models.ImageField(
        upload_to="headimage", blank=True, null=True, verbose_name="头像"
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "聊天用户信息"
        verbose_name_plural = verbose_name
        


class Room(models.Model):
    '''聊天室模型'''
    name = models.CharField(max_length=128)
    online = models.ManyToManyField(to=ChatUser, blank=True)

    def get_online_count(self):
        return self.online.count()

    def join(self, user):
        self.online.add(user)
        self.save()

    def leave(self, user):
        self.online.remove(user)
        self.save()

    def __str__(self):
        return f'{self.name} ({self.get_online_count()})'
    
    class Meta:
        verbose_name = "聊天室信息"
        verbose_name_plural = verbose_name


class Message(models.Model):
    '''消息模型'''
    user = models.ForeignKey(to=ChatUser, on_delete=models.CASCADE)
    room = models.ForeignKey(to=Room, on_delete=models.CASCADE)
    content = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.content} [{self.timestamp}]'
    
    class Meta:
        verbose_name = "消息"
        verbose_name_plural = verbose_name