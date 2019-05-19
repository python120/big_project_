from django.conf.urls import url

from users import views

urlpatterns = [
    # 注册
    url(r'^register/$', views.RegisterView.as_view(), name='register'),
    # 用户名重复
    url(r'^usernames/(?P<username>[a-zA-Z0-9_-]{5,20})/count/$', views.UsernameCountView.as_view()),
    # 手机号重复
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', views.MobileCountView.as_view()),
    # 登录
    url(r"^login/$", views.LoginView.as_view(), name="login"),
    # 退出登录
    url(r"^logout/$", views.LogoutView.as_view(), name="logout"),
    # 用户中心
    url(r'^info/$', views.UserInfoView.as_view(), name='info'),
    # 添加邮箱
    url(r'^emails/$', views.EmailView.as_view(), name="emails"),
    # 激活邮箱
    url(r'^emails/verification/$', views.VerifyEmailView.as_view()),
    # 用户收货地址
    url(r'^addresses/$', views.AddressView.as_view(), name='address'),
    # 新增收货地址
    url(r'^addresses/create/$', views.CreateAddressView.as_view()),
    # 收货地址修改和删除
    url(r'^addresses/(?P<address_id>\d+)/$', views.UpdateDestroyAddressView.as_view()),
    # 设置用户默认收货地址
    url(r'^addresses/(?P<address_id>\d+)/default/$', views.DefaultAddressView.as_view()),
    # 修改地址标题
    url(r'^addresses/(?P<address_id>\d+)/title/$', views.UpdateTitleAddressView.as_view()),
    # 修改密码
    url(r'^password/$', views.ChangePasswordView.as_view()),
    #　登录用户的浏览记录存储与读取
    url(r'^browse_histories/$', views.UserBrowseHistory.as_view()),
    # 忘记密码请求
    url(r'^find_password/$',views.FindPasswordView.as_view(), name="find_password"),
    # 第一步用户输入图片验证码和用户名
    url(r'^accounts/(?P<username>\w+)/sms/token/$', views.FirstView.as_view()),
    # 验证access_token决定是否发送短信
    url(r'^sms_codes/$', views.SecondView.as_view()),
    # 短信已发送用户点击下一步,校验验证码是否正确
    url(r'^accounts/(?P<username>\w+)/password/token/$', views.ThirdView.as_view()),
    # 用户尝试性修改密码并提交表单
    url(r'^users/(?P<user_id>\d+)/password/$', views.FourView.as_view()),
    # 获取用户微博信息
    url(r'^users/sina/$', views.UsersSinaView.as_view()),
]
