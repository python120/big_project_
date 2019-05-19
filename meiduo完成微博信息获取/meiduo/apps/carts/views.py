from django.shortcuts import render
from django.views import View
from django import http
from django_redis import get_redis_connection
import pickle, base64, json

from goods.models import SKU
from meiduo.utils.view import LoginRequiredJSONMixin
from meiduo.utils.response_code import RETCODE
# Create your views here.

class CartsView(View):
    """购物车管理"""
    def post(self, request):
        """添加购物车"""
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get("sku_id")
        count = json_dict.get("count")
        selected = json_dict.get("selected", True)

        # 校验参数
        if not all([sku_id, count]):
            return http.HttpResponseForbidden("缺少必传参数")

        try:
            SKU.objects.get(id=sku_id)
            count = int(count)
        except Exception as e:
            return http.HttpResponseForbidden(e)

        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('selected错误')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '添加购物车成功'})
        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()  # 连接redis
            
            pl.hincrby("carts_%s" % user.id, sku_id, count)
            if selected:
                pl.sadd("selected_%s" % user.id, sku_id)
            pl.execute()  # 添加购物车
            
        else:
            # 用户未登录，操作cookie购物车
            cart_dict = request.COOKIES.get('carts', {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))
            # 获取到cookie中的carts购物车

            # 判断要加入购物车的商品是否已经在购物车中,如有相同商品，累加求和，反之，直接赋值
            if sku_id in cart_dict:
                count += cart_dict.get(sku_id).get('count')

            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符
            cart_dict = base64.b64encode(pickle.dumps(cart_dict)).decode()

            # 将购物车数据写入到cookie
            response.set_cookie('carts', cart_dict, max_age=3600)

        # 响应Json对象
        return response

    def get(self, request):
        """展示购物车"""
        user = request.user
        if user.is_authenticated:
            # 查询redis购物车
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)

            # 构造cart_dict: {sku_id:{}, sku_id2: {}}
            # {} : {'count': count, 'selected': T/F}
            cart_dict = dict()
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in cart_selected
                }

        else:
            # 查询cookie购物车
            cart_dict = request.COOKIES.get("carts", {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))

        # 构建响应数据
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        cart_skus = list()

        for sku in skus:
            cart_skus.append({
                'id': sku.id,
                'name':sku.name,
                'count': cart_dict.get(sku.id).get('count'),
                # 将True，转'True'，方便json解析
                'selected': str(cart_dict.get(sku.id).get('selected')),
                'default_image_url': sku.default_image.url,
                # 从Decimal('10.2')中取出'10.2'，方便json解析
                'price': str(sku.price),
                'amount': str(sku.price * cart_dict.get(sku.id).get('count'))
            })

        return render(request, 'cart.html', {'cart_skus': cart_skus})

    def put(self, request):
        """修改购物车"""
        # 接受参数
        json_dict = json.loads(request.body.decode())
        sku_id = json_dict.get('sku_id')
        count = json_dict.get('count')
        selected = json_dict.get('selected', True)
        # 校验参数
        # 判断参数是否齐全
        if not all([sku_id, count]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断sku_id是否存在
        try:
            sku = SKU.objects.get(id=sku_id)
        except models.SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品sku_id不存在')
        # 判断count是否为数字
        try:
            count = int(count)
        except Exception:
            return http.HttpResponseForbidden('参数count有误')
        # 判断selected是否为bool值
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        # 创建响应对象
        cart_sku = {
            'id':sku_id,
            'count':count,
            'selected':selected,
            'name': sku.name,
            'default_image_url': sku.default_image.url,
            'price': sku.price,
            'amount': sku.price * count,
        }
        response = http.JsonResponse({'code':RETCODE.OK, 'errmsg':'修改购物车成功', 'cart_sku':cart_sku})

        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，修改redis购物车
            redis_conn = get_redis_connection('carts')
            pl = redis_conn.pipeline()
            pl.hset("carts_%s" % user.id, sku_id, count)
            if selected:
                pl.sadd('selected_%s' % user.id, sku_id)
            else:
                pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()

        else:
            # 用户未登录，修改cookie购物车
            cart_dict = request.COOKIES.get("carts", {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))
            cart_dict[sku_id] = {
                'count': count,
                'selected': selected
            }

            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
            cart_dict = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_dict, max_age=3600)

        return response

    def delete(self, request):
        """删除购物车"""
        # 接受并校验参数
        sku_id = json.loads(request.body.decode()).get("sku_id")
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('商品不存在')
        
        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '删除购物车成功'})

        # 判断用户是否登录
        user = request.user
        if user is not None and user.is_authenticated:
            # 用户未登录，删除redis购物车
            pl = get_redis_connection('carts').pipeline()
            pl.hdel("carts_%s" % user.id, sku_id)
            pl.srem('selected_%s' % user.id, sku_id)
            pl.execute()
        else:
            # 用户未登录，删除cookie购物车
            cart_dict = request.COOKIES.get("carts", {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
            cart_dict = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_dict, max_age=3600)

        return response


class CartsSelectAllView(View):
    """全选购物车"""

    def put(self, request):
        # 接受参数
        selected = json.loads(request.body.decode()).get('selected')
        # 校验参数
        if selected:
            if not isinstance(selected, bool):
                return http.HttpResponseForbidden('参数selected有误')

        response = http.JsonResponse({'code': RETCODE.OK, 'errmsg': '全选购物车成功'})

        # 判断用户是否登录
        user = request.user
        if user is not None and user.is_authenticated:
            # 用户已登录，操作redis购物车
            redis_conn = get_redis_connection('carts')
            redis_cart = redis_conn.hgetall("carts_%s" % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)
            sku_id_list = redis_cart.keys()
            if selected:
                # 全选
                redis_conn.sadd('selected_%s' % user.id, *sku_id_list)
            else:
                # 全不选
                redis_conn.srem('selected_%s' % user.id, *sku_id_list)

        else:
            # 用户已登录，操作cookie购物车
            cart_dict = request.COOKIES.get("carts", {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))
            for sku_id in cart_dict:
                cart_dict[sku_id]['selected'] = selected

            # 将字典转成bytes,再将bytes转成base64的bytes,最后将bytes转字符串
            cart_dict = base64.b64encode(pickle.dumps(cart_dict)).decode()
            response.set_cookie('carts', cart_dict, max_age=3600)

        return response


class CartsSimpleView(View):
    """商品页面右上角购物车"""

    def get(self, request):
        # 判断用户是否登录
        user = request.user
        if user.is_authenticated:
            # 用户已登录，查询Redis购物车
            redis_conn = get_redis_connection('carts')  # 拿不用pl存用pl
            # pl作为StrictRedis对象 没有hgetall方法
            redis_cart = redis_conn.hgetall('carts_%s' % user.id)
            cart_selected = redis_conn.smembers('selected_%s' % user.id)
            
            cart_dict = {}
            for sku_id, count in redis_cart.items():
                cart_dict[int(sku_id)] = ({
                    'count': int(count),
                    'selected': sku_id in cart_selected
                })

        else:
            # 用户未登录，查询cookie购物车
            cart_dict = request.COOKIES.get("carts", {})
            if cart_dict:
                cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))

        # 构造简单购物车JSON数据
        cart_skus = list()
        sku_ids = cart_dict.keys()
        skus = SKU.objects.filter(id__in=sku_ids)
        for sku in skus:
            cart_skus.append({
                'id':sku.id,
                'name':sku.name,
                'count':cart_dict.get(sku.id).get('count'),
                'default_image_url': sku.default_image.url
            })

        # 响应json列表数据
        return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'cart_skus':cart_skus})
