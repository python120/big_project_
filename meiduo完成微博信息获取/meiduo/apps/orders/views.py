from django.shortcuts import render
from django.views.generic import View
from django_redis import get_redis_connection
from decimal import Decimal
from django.utils import timezone
from django import http
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage
import json

from meiduo.utils.view import LoginRequiredMixin, LoginRequiredJSONMixin
from meiduo.utils.response_code import RETCODE
from goods.models import SKU
from users.models import Address
from orders.models import OrderInfo, OrderGoods
import logging

logger = logging.getLogger('django')

# Create your views here.

class OrderSettlementView(LoginRequiredMixin, View):
    """结算订单"""
    def get(self, request):
        """提供订单结算页面"""

        # 获取登录用户
        user = request.user
        # 获取用户地址
        try:
            addresses = Address.objects.filter(user=user, is_deleted=False)
        except Address.DoesNotExist:
            # 如果地址为空，渲染模板时会判断，并跳转到地址编辑页面
            addresses = None
        # 从Redis购物车中查询出被勾选的商品信息
        # redis_conn = get_redis_connection('carts')
        # redis_cart = redis_conn.hgetall("carts_%s" % user.id)
        # cart_selected = redis_conn.smembers("selected_%s" % user.id)
        pl = get_redis_connection('carts').pipeline()
        pl.hgetall("carts_%s" % user.id)
        pl.smembers("selected_%s" % user.id)
        ret_list = pl.execute()
        redis_cart = ret_list[0]
        cart_selected = ret_list[1]

        cart_dict = dict()
        for sku_id in cart_selected:
            cart_dict[int(sku_id)] = int(redis_cart[sku_id])

        total_count = 0
        total_amount = Decimal("8.00")
        
        # 查询商品信息
        skus = SKU.objects.filter(id__in=cart_dict.keys())
        for sku in skus:
            sku.count = cart_dict[sku.id]
            sku.amount = sku.price * sku.count
            total_count += sku.count
            total_amount += sku.amount

        # 补充运费
        freight = Decimal('10.00')


        # 渲染界面
        context = {
            'addresses': addresses,
            'skus': skus,
            'total_count': total_count,
            'total_amount': total_amount,
            'freight': freight,
            'payment_amount':total_amount + freight
        }
        return render(request, "place_order.html", context)


class OrderCommitView(LoginRequiredJSONMixin, View):
    """订单提交"""

    def post(self, request):
        """保存订单信息和订单商品信息"""
        # 获取当前要保存的订单数据
        json_dict = json.loads(request.body.decode())
        address_id = json_dict.get('address_id')
        pay_method = json_dict.get('pay_method')
        # 校验参数
        if not all([address_id, pay_method]):
            return http.HttpResponseForbidden('缺少必传参数')
        # 判断address_id是否合法
        try:
            address = Address.objects.get(id=address_id)
        except Exception:
            return http.HttpResponseForbidden('参数address_id错误')
        # 判断pay_method是否合法
        if pay_method not in [OrderInfo.PAY_METHODS_ENUM['CASH'], OrderInfo.PAY_METHODS_ENUM['ALIPAY']]:
            return http.HttpResponseForbidden('参数pay_method错误')

        # 获取登录用户
        user = request.user
        # 生成订单编号：年月日时分秒+用户编号
        order_id = timezone.localtime().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)

        # 显式的开启一个事务
        with transaction.atomic():
            # 创建事务保存点
            save_id = transaction.savepoint()

            # 暴力回滚
            try:
                # 保存订单基本信息 OrderInfo（一）
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal('0'),
                    freight=Decimal('10.00'),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNPAID'] if pay_method == OrderInfo.PAY_METHODS_ENUM['ALIPAY'] else
                    OrderInfo.ORDER_STATUS_ENUM['UNSEND']
                )

                # 从redis读取购物车中被勾选的商品信息
                redis_conn = get_redis_connection('carts')
                redis_cart = redis_conn.hgetall('carts_%s' % user.id)
                selected = redis_conn.smembers('selected_%s' % user.id)
                carts = {}
                for sku_id in selected:
                    carts[int(sku_id)] = int(redis_cart[sku_id])
                sku_ids = carts.keys()

                # 遍历购物车中被勾选的商品信息
                for sku_id in sku_ids:
                    while True:
                        # 查询SKU信息
                        sku = SKU.objects.get(id=sku_id)
                        # 判断SKU库存
                        sku_count = carts[sku.id]
                        if sku_count > sku.stock:
                            transaction.savepoint_rollback(save_id)
                            return http.JsonResponse({'code': RETCODE.STOCKERR, 'errmsg': '库存不足'})

                        import time
                        time.sleep(3)
                        # SKU减少库存，增加销量
                        # sku.stock -= sku_count
                        # sku.sales += sku_count
                        # sku.save()
                        # 乐观锁
                        result = SKU.objects.filter(id=sku_id, stock=sku.stock, sales=sku.sales).update(stock=sku.stock-sku_count, sales=sku.sales+sku_count)
                        if result == 0:
                            continue



                        # 修改SPU销量
                        sku.spu.sales += sku_count
                        sku.spu.save()

                        # 保存订单商品信息 OrderGoods（多）
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price,
                        )

                        # 保存商品订单中总价和总数量
                        order.total_count += sku_count
                        order.total_amount += (sku_count * sku.price)

                        break

                # 添加邮费和保存订单信息
                order.total_amount += order.freight
                order.save()
            except Exception:
                transaction.savepoint_rollback(save_id)
                return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '下单失败'})

            transaction.savepoint_commit(save_id)

        # 清除购物车中已结算的商品
        pl = redis_conn.pipeline()
        pl.hdel('carts_%s' % user.id, *selected)
        pl.srem('selected_%s' % user.id, *selected)
        pl.execute()

        # 响应提交订单结果
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '下单成功', 'order_id': order.order_id})


class OrderSuccessView(LoginRequiredMixin, View):
    """提交订单成功"""

    def get(self, request):
        order_id = request.GET.get('order_id')
        payment_amount = request.GET.get('payment_amount')
        pay_method = request.GET.get('pay_method')

        context = {
            'order_id':order_id,
            'payment_amount':payment_amount,
            'pay_method':pay_method
        }
        return render(request, 'order_success.html', context)


class UserOrderInfoView(LoginRequiredMixin, View):
    """我的订单"""

    def get(self, request, page_num):
        """提供我的订单页面"""
        user = request.user
        # 查询订单
        orders = OrderInfo.objects.filter(user=user).order_by("-create_time")
        # 遍历所有订单
        for order in orders:
            # 绑定订单状态
            order.status_name = OrderInfo.ORDER_STATUS_CHOICES[order.status-1][1]
            # 绑定支付方式
            order.pay_method_name = OrderInfo.PAY_METHOD_CHOICES[order.pay_method-1][1]
            order.sku_list = []
            # 查询订单商品
            order_goods = order.skus.all()
            # 遍历订单商品
            for order_good in order_goods:
                sku = order_good.sku
                sku.count = order_good.count
                sku.amount = sku.price * sku.count
                order.sku_list.append(sku)
        # 分页
        page_num = int(page_num)
        try:
            paginator = Paginator(orders, 2)
            page_orders = paginator.page(page_num)
            total_page = paginator.num_pages
        except EmptyPage:
            return http.HttpResponseForbidden('订单不存在')

        context = {
            "page_orders": page_orders,
            'total_page': total_page,
            'page_num': page_num,
        }
        return render(request, "user_center_order.html", context)


class OrderCommentView(LoginRequiredMixin, View):
    """订单商品评价"""

    def get(self, request):
        """展示商品评价页面"""
        # 接收参数
        order_id = request.GET.get('order_id')
        # 校验参数
        try:
            OrderInfo.objects.get(order_id=order_id, user=request.user)
        except OrderInfo.DoesNotExist:
            return http.HttpResponseNotFound('订单不存在')

        # 查询订单中未被评价的商品信息
        try:
            uncomment_goods = OrderGoods.objects.filter(order_id=order_id, is_commented=False)
        except Exception:
            return http.HttpResponseServerError('订单商品信息出错')

        # 构造待评价商品数据
        uncomment_goods_list = []
        for goods in uncomment_goods:
            uncomment_goods_list.append({
                'order_id':goods.order.order_id,
                'sku_id':goods.sku.id,
                'name':goods.sku.name,
                'price':str(goods.price),
                'default_image_url':goods.sku.default_image.url,
                'comment':goods.comment,
                'score':goods.score,
                'is_anonymous':str(goods.is_anonymous),
            })

        # 渲染模板
        context = {
            'uncomment_goods_list': uncomment_goods_list
        }
        return render(request, 'goods_judge.html', context)

    
    def post(self, request):
        """评价订单商品"""
        # 接收参数
        json_dict = json.loads(request.body.decode())
        order_id = json_dict.get('order_id')
        sku_id = json_dict.get('sku_id')
        score = json_dict.get('score')
        comment = json_dict.get('comment')
        is_anonymous = json_dict.get('is_anonymous')
        # 校验参数
        if not all([order_id, sku_id, score, comment]):
            return http.HttpResponseForbidden('缺少必传参数')
        try:
            OrderInfo.objects.filter(order_id=order_id, user=request.user, status=OrderInfo.ORDER_STATUS_ENUM['UNCOMMENT'])
        except OrderInfo.DoesNotExist:
            return http.HttpResponseForbidden('参数order_id错误')
        try:
            sku = SKU.objects.get(id=sku_id)
        except SKU.DoesNotExist:
            return http.HttpResponseForbidden('参数sku_id错误')
        if is_anonymous:
            if not isinstance(is_anonymous, bool):
                return http.HttpResponseForbidden('参数is_anonymous错误')

        # 保存订单商品评价数据
        OrderGoods.objects.filter(order_id=order_id, sku_id=sku_id, is_commented=False).update(
            comment=comment,
            score=score,
            is_anonymous=is_anonymous,
            is_commented=True
        )

        # 累计评论数据
        sku.comments += 1
        sku.save()
        sku.spu.comments += 1
        sku.spu.save()

        # 如果所有订单商品都已评价，则修改订单状态为已完成
        if OrderGoods.objects.filter(order_id=order_id, is_commented=False).count() == 0:
            OrderInfo.objects.filter(order_id=order_id).update(status=OrderInfo.ORDER_STATUS_ENUM['FINISHED'])
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '评价成功'})


    class GoodsCommentView(View):
        """订单商品评价信息"""

        def get(self, request, sku_id):
            # 获取被评价的订单商品信息
            order_goods_list = OrderGoods.objects.filter(sku_id=sku_id, is_commented=True).order_by('-create_time')[:30]
            # 序列化
            comment_list = []
            for order_goods in order_goods_list:
                username = order_goods.order.user.username
                comment_list.append({
                    'username': username[0] + '***' + username[-1] if order_goods.is_anonymous else username,
                    'comment':order_goods.comment,
                    'score':order_goods.score,
                })
            return http.JsonResponse({'code':RETCODE.OK, 'errmsg':'OK', 'comment_list': comment_list})

