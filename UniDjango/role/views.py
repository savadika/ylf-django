from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from django.db import transaction
from .models import SysRole, SysUserRole
from menu.models import SysMenu
from menu.models import SysRoleMenu
from utils.filters import create_complex_filter_class
from utils.permissions import permission_required_for_action
from utils.viewsets import BaseModelViewSet
from utils.response import Ok
from utils.exceptions import ApiException
from utils.serializers import BaseModelSerializer


class SysRoleSerializer(BaseModelSerializer):
    class Meta:
        model = SysRole
        fields = ('id', 'name', 'code', 'create_time', 'update_time', 'remark')


class SysRoleViewSet(BaseModelViewSet):
    """
    角色资源：提供列表、详情、创建、更新、局部更新、删除
    路由由 SimpleRouter 生成：/department 与 /department/{id}
    支持分页功能和高级搜索功能
    
    支持的搜索参数：
    - name: 角色名称模糊搜索
    - remark: 备注模糊搜索
    - create_time_start/create_time_end: 创建时间范围
    - update_time_start/update_time_end: 更新时间范围
    - search: 全局搜索（搜索部门名称和备注）
    """
    queryset = SysRole.objects.all().order_by('id')  # 查询集
    serializer_class = SysRoleSerializer             # 序列化器
    permission_classes = [permission_required_for_action({
        'list': 'system:role:list',
        'retrieve': 'system:role:query',
        'create': 'system:role:add',
        'update': 'system:role:edit',
        'partial_update': 'system:role:edit',
        'destroy': 'system:role:delete',
        'menus': 'system:role:permission',
        'update_permissions': 'system:role:permission',
        'advanced_search': 'system:role:list',
        'filter_options': 'system:role:list',
    })]
    filterset_class = create_complex_filter_class(SysRole, search_fields=['name', 'code', 'remark'])  # 动态创建的过滤器类，查询
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']   # 允许的HTTP方法

    def perform_destroy(self, instance):
        """删除角色前先清理角色菜单和用户角色关联。"""
        with transaction.atomic():
            SysUserRole.objects.filter(role=instance).delete()
            SysRoleMenu.objects.filter(role=instance).delete()
            instance.delete()

    @action(detail=True, methods=['get'])
    def menus(self, request, pk=None):
        """
        获取指定角色的菜单树和权限列表
        url: /role/{id}/menus/
        """
        role = self.get_object()
        menu_tree, permissions = role.get_role_menus()  
        return Ok(data={
            'menus': menu_tree,
            'permissions': permissions
        })

    @action(detail=True, methods=['put'], url_path='permissions')
    def update_permissions(self, request, pk=None):
        """
        更新角色权限（自定义）
        url: /role/{id}/permissions/
        method: PUT
        body: { "permissions": [1, 2, 3, ...] }
        """
        role = self.get_object()
        permissions = request.data.get('permissions', [])
        
        if not isinstance(permissions, list):
            raise ApiException('permissions must be a list', status_code=400)

        unique_menu_ids = set()
        for menu_id in permissions:
            try:
                unique_menu_ids.add(int(menu_id))
            except (TypeError, ValueError):
                raise ApiException('permissions 中只能包含菜单 ID', status_code=400)

        if unique_menu_ids:
            valid_count = SysMenu.objects.filter(id__in=unique_menu_ids).count()
            if valid_count != len(unique_menu_ids):
                raise ApiException('存在无效的菜单 ID', status_code=400)

        with transaction.atomic():
            # 1. 删除旧的权限
            SysRoleMenu.objects.filter(role=role).delete()
            
            # 2. 插入新的权限
            new_relations = [SysRoleMenu(role=role, menu_id=menu_id) for menu_id in unique_menu_ids]
            if new_relations:
                SysRoleMenu.objects.bulk_create(new_relations)

        return Ok(data=None)



# Create your views here.
