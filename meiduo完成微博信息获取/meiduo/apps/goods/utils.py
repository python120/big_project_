from goods.models import GoodsCategory

def get_breadcrumb(category):
    """
    获取面包屑导航
    :param category: 商品类别
    :return: 面包屑导航字典
    """
    # category 应该是3级数据对象
    breadcrumb = dict(
        cat1=category.parent.parent,
        cat2=category.parent,
        cat3=category
    )

    return breadcrumb