from django.shortcuts import render
from django.views import View

from contents.utils import get_categories
from contents.models import ContentCategory
# Create your views here.

class IndexView(View):
    """首页广告"""

    def get(self, request):
        """提供首页广告界面"""
        categories = get_categories()

        contents = {}  # 广告信息
        # 查询所有的广告的类别
        content_categories = ContentCategory.objects.all()

        for cat in content_categories:
            contents[cat.key] = cat.content_set.filter(status=True).order_by('sequence')

        # 渲染模板的上下文
        context = {
            'categories': categories,
            'contents': contents,
        }
        return render(request, 'index.html', context)
