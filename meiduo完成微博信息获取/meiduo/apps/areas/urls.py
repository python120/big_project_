from django.conf.urls import url

from areas import views


urlpatterns = [
    # 获取省市区数据
    url(r'^areas/$', views.AreasView.as_view()),
]