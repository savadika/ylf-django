from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import SysMenu, SysMenuSerializer, SysRoleMenu
from utils.pagination import CustomPageNumberPagination
from utils.filters import create_complex_filter_class
from utils.permissions import permission_required_for_action
from utils.menu_tree import build_menu_tree

class SysMenuViewSet(viewsets.ModelViewSet):
    """
    菜单资源：提供列表、详情、创建、更新、局部更新、删除
    """
    queryset = SysMenu.objects.all().order_by('order_num', 'id')
    serializer_class = SysMenuSerializer
    permission_classes = [permission_required_for_action({
        'list': 'system:menu:list',
        'retrieve': 'system:menu:query',
        'create': 'system:menu:add',
        'update': 'system:menu:edit',
        'partial_update': 'system:menu:edit',
        'destroy': 'system:menu:delete',
        'get_all_menus': 'system:menu:list',
    })]
    pagination_class = CustomPageNumberPagination
    filterset_class = create_complex_filter_class(SysMenu, search_fields=['name', 'path', 'component', 'perms', 'remark'])
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def perform_destroy(self, instance):
        """删除菜单前先清理整棵子树上的角色菜单关联。"""
        menu_ids = {instance.id}
        pending = [instance.id]
        while pending:
            children = list(
                SysMenu.objects.filter(parent_id__in=pending).values_list('id', flat=True)
            )
            menu_ids.update(children)
            pending = children

        with transaction.atomic():
            SysRoleMenu.objects.filter(menu_id__in=menu_ids).delete()
            instance.delete()

    @action(detail=False, methods=['get'])
    def get_all_menus(self, request):
        """
        获取所有菜单（树形结构），包含按钮
        通常用于菜单管理页面展示，或角色授权时的菜单树选择
        url: /menu/get_all_menus/
        """
        menus = SysMenu.objects.all().order_by('order_num', 'id')
        roots, _ = build_menu_tree(menus)

        return Response({
            'code': 200,
            'data': roots
        })
