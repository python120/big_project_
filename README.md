# MDCK
#上线后看meiduo.log文件日志记录

#开发host.js 8000端口  更改open.weibo.com中回调地址使用dev.py
#生产host.js 80端口   更改open.weibo.com中回调地址使用prod.py

# 模型类uid属性更改为access_token(数据库不同可能会报错)
# spike.port固定为80,秒杀入口为首页轮播图
# 主从功能关闭
# uwsgi 启动链接nginx.socket=127.0.0.1:8001
# nginx静态文件位置8888:   /Desktop/M00/MDCK/meiduo/static
# 后端www.meiduo.site/admin
# goods.admin 异步生产detail.html
