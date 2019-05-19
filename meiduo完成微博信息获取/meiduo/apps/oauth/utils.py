from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadData
from django.conf import settings
import requests, json
from urllib.parse import urlencode, parse_qs
from django_redis import get_redis_connection

from oauth import constants

def generate_eccess_token(openid):
    """
    签名openid
    :param openid: 用户的openid
    :return: access_token
    """
    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.ACCESS_TOKEN_EXPIRES)
    data = {'openid': openid}
    token = serializer.dumps(data)
    return token.decode()


def check_access_token(openid):
    """
        签名的openid解密
        :param openid: 要解密的openid
        :return: 解密后的openid
        """
    serializer = Serializer(settings.SECRET_KEY, expires_in=constants.ACCESS_TOKEN_EXPIRES)
    try:
        data = serializer.loads(openid)
    except BadData:
        return None
    return data['openid']


class SinaLoginTool(object):
    """微博登录工具"""
# https://api.weibo.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=YOUR_REGISTERED_REDIRECT_URI
# 如果用户同意授权,页面跳转至 YOUR_REGISTERED_REDIRECT_URI/?code=CODE：
# 换取Access Token：
# https://api.weibo.com/oauth2/access_token?client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET&grant_type=authorization_code&redirect_uri=YOUR_REGISTERED_REDIRECT_URI&code=CODE
    def __init__(self, client_id=None, client_secret=None, redirect_uri=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.grant_type="authorization_code"
        self.redirect_uri = redirect_uri
        self.response_type = "code"


    def get_login_url(self):
        # 微博登录url参数组建
        oauth_dict = {"client_id":self.client_id,"response_type":self.response_type,"redirect_uri":self.redirect_uri}
        oauth_string = urlencode(oauth_dict)
        login_url = 'https://api.weibo.com/oauth2/authorize?'+oauth_string
        return login_url

    def get_access_token(self, code):
        """获取当前微博用户的access_token"""
        oauth_dict = {"client_id":self.client_id,"client_secret":self.client_secret,"grant_type":self.grant_type,"redirect_uri":self.redirect_uri,"code":code}
        oauth_string = urlencode(oauth_dict)
        url = "https://api.weibo.com/oauth2/access_token?"+oauth_string
        try:
            response = requests.post(url)
            text = response.content.decode()
            access_token = json.loads(text).get("access_token")
            uid = json.loads(text).get("uid")
            redis_conn = get_redis_connection("verify_code")
            redis_conn.setex("uid_%s" % access_token, 3600, uid)  # 将uid存至redis可以通过唯一access_token取出唯一uid
        except Exception:
            access_token = None
        return access_token

    def get_sina_user_msg(self, access_token, uid):
        """获取用户的微博信息"""
        # access_token uid get方式
        # https://api.weibo.com/2/users/show.json
        oauth_dict = {"access_token":access_token,"uid":int(uid)}
        url = "https://api.weibo.com/2/users/show.json"
        response = requests.get(url, params=oauth_dict)
        result = response.content.decode()
        result = json.loads(result)
        sina_img_url = result.get("profile_image_url")
        sina_user_name = result.get("screen_name")
        profile_url = result.get("profile_url")
        print(sina_img_url,sina_user_name,profile_url)
        context = {"sina_img_url":sina_img_url,"sina_user_name":sina_user_name,"profile_url":profile_url}
        return context

