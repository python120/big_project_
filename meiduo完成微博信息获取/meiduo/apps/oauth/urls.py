from django.conf.urls import url

from oauth import views

urlpatterns = [
    # 获取QQ登录链接
    url(r'^qq/authorization/$', views.QQAuthURLView.as_view()),
    # QQ扫码登录后的回调
    url(r'^oauth_callback$', views.QQAuthUserView.as_view()),
    # 获取微博登录链接
    url(r'^sina/authorization/$', views.SinaLoginView.as_view()),
    # 微博登录后的毁掉地址
    url(r'^sina_callback$', views.SinaCallbackView.as_view()),
]