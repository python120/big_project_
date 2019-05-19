# 1. 导入FastDFS客户端扩展
import pprint

from fdfs_client.client import Fdfs_client
# 2. 创建FastDFS客户端实例
client = Fdfs_client('./client.conf')
# 3. 调用FastDFS客户端上传文件方法
ret = client.upload_by_filename('/home/python/Desktop/kk.jpg')
print(ret)