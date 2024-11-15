from django import forms
from . import models
from django.core.exceptions import ValidationError
 
 
class signup_form(forms.Form):
    username = forms.CharField(
        max_length=20,
        label='登录账号',
        error_messages={"max_length": "登录账号不能超过20位", "required": "登录账号不能为空"},
        widget=forms.widgets.TextInput(
            attrs={"class": "form-control"},
        )
    )
    password = forms.CharField(
        min_length=6,
        label='密码',
        error_messages={'min_length': '密码最少6位', "required": "密码不能为空", },
        widget=forms.widgets.PasswordInput(
            attrs={'class': 'form-control'},
            render_value=True,
        )
    )
    repassword = forms.CharField(
        min_length=6,
        label='确认密码',
        error_messages={'min_length': '密码最少6位', "required": "密码不能为空", },
        widget=forms.widgets.PasswordInput(
            attrs={'class': 'form-control'},
            render_value=True,
        )
    )
    nickname = forms.CharField(
        max_length=20,
        required=False,
        label='昵称',
        error_messages={'max_length': '姓名长度不能超过20位', },
        initial='钱多多',
        widget=forms.widgets.TextInput(
            attrs={'class': 'form-control'}
        )
    )
    email = forms.EmailField(
        label='邮箱',
        error_messages={'invalid': '邮箱格式不对', 'required': '邮箱不能为空', },
        widget=forms.widgets.EmailInput(attrs={'class': 'form-control', }
                                        )
    )
    phone = forms.CharField(
        label='电话号码',
        required=False,
        error_messages={'max_length': '最大长度不超过11位', },
        widget=forms.widgets.TextInput(
            attrs={'class': 'form-control'}
        )
    )
    img = forms.ImageField(
        label='头像',
        widget=forms.widgets.FileInput(
            # 在attrs中设置style为display:none是为了在页面中不显示这个标签
            attrs={'style': "display: none"}
        )
    )
 
    def clean_username(self):
        """定义一个校验字段的函数，校验字段函数命名是有规则的，形式：clean_字段名()这个函数保证username值不重复"""
        # 取得字段值，clean_data保存着通过第一步is_vaild()校验的各字段值，是字典类型
        # 因此要用get()函数取值
        uname = self.cleaned_data.get('username')
        # 从数据库表中查询是否有同名的记录
        vexist = models.ChatUser.objects.filter(username=uname)
        if vexist:
            # 如果有同名记录，增加一条错误信息给该字段的errors属性
            self.add_error('username', ValidationError('登录账号已存在!'))
        else:
            return uname
 
    def clean_repassword(self):
        '''定义一个校验程序，判断两次输入的密码是否一致'''
        passwd = self.cleaned_data.get('password')
        repasswd = self.cleaned_data.get('repassword')
        if repasswd and repasswd != passwd:
            self.add_error('repassword', ValidationError('两次输入的密码不一致'))
        else:
            return repasswd