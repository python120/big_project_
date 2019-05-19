from django_redis import get_redis_connection
import pickle, base64


def merge_cart_cookie_to_redis(request, user, response):
    """登录时将cookie购物车合并到redis购物车"""
    
    # 获取cookie购物车
    cart_dict = request.COOKIES.get("carts", {})
    if not cart_dict:  # 如果cookie购物车空，则不合并
        return response

    cart_dict = pickle.loads(base64.b64decode(cart_dict.encode()))
    
    pl = get_redis_connection('carts').pipeline()  # 链接redis

    # 遍历cookie购物车大字典,把sku_id及count向redis的hash中存储
    for sku_id in cart_dict:
        pl.hset('carts_%s' % user.id, sku_id, cart_dict.get(sku_id).get('count'))
        if cart_dict.get(sku_id).get('selected'):
            pl.sadd('selected_%s' % user.id, sku_id)
        else:
            pl.srem('selected_%s' % user.id, sku_id)
    pl.execute()

    response.delete_cookie('carts')  # 删除cookie购物车

    return response


