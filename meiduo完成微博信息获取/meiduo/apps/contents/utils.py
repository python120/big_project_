from collections import OrderedDict

from goods.models import GoodsChannel


def get_categories():
    # 查询商品频道和分类
    categories = OrderedDict()

    # 37个频道
    channels = GoodsChannel.objects.order_by("group_id", "sequence")

    for channel in channels:
        group_id = channel.group_id
        if group_id not in categories:
            # 创建11　个键值对　categories = {1:{..}, 2: {..},...}
            categories[group_id] = {"channels": [], 'sub_cats': []}

        # 查询和当前频道唯一对应的一级数据
        cat1 = channel.category

        categories[group_id]["channels"].append(cat1)  # 将一级数据填充到对应组的channels中

        cat2_qs = cat1.subs.all()  # 查询出当前一级数据对应的所以二级数据

        for cat2 in cat2_qs:
            # 给每一个二级数据添加属性　绑定对应的三级数据
            cat2.sub_cats = cat2.subs.all()
            # 讲二级数据对象添加质sub_cats中
            categories[group_id]["sub_cats"].append(cat2)

    return categories