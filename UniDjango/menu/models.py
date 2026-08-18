from django.db import models
from rest_framework import serializers

from role.models import SysRole


# Create your models here.

class SysMenu(models.Model):
    """
    菜单表
    """
    id = models.AutoField(primary_key=True, verbose_name='菜单ID')
    name = models.CharField(max_length=50, unique=True, verbose_name='菜单名称')
    icon = models.CharField(max_length=50, null=True, verbose_name='菜单图标')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        verbose_name='父菜单ID',
    )
    order_num = models.IntegerField(null=True, verbose_name='排序号')
    path = models.CharField(max_length=200, null=True, verbose_name='菜单路径')
    component = models.CharField(max_length=200, null=True, verbose_name='组件路径')
    menu_type = models.CharField(max_length=20, null=True, verbose_name='菜单类型')  # 'M' for menu, 'C' for component, 'F' for Button
    perms = models.CharField(max_length=100, null=True, verbose_name='权限标识')  # 权限标识，格式为：system:user:add
    create_time = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')
    remark = models.CharField(max_length=200, null=True, verbose_name='备注')

    class Meta:
        db_table = 'sys_menu'
        verbose_name = '菜单表'
        verbose_name_plural = verbose_name
       


class SysMenuSerializer(serializers.ModelSerializer):
    """
    菜单序列化器
    """
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent',
        queryset=SysMenu.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SysMenu
        fields = ('id', 'name', 'icon', 'parent_id', 'order_num', 'path', 'component', 'menu_type', 'perms', 'remark')

    def _get_descendant_ids(self, root_id):
        """返回指定菜单的全部后代 ID，用于防止把父级指向自己的子树。"""
        descendant_ids = set()
        pending = [root_id]
        while pending:
            child_ids = list(
                SysMenu.objects.filter(parent_id__in=pending).values_list('id', flat=True)
            )
            descendant_ids.update(child_ids)
            pending = child_ids
        return descendant_ids

    def validate(self, attrs):
        parent = attrs.get('parent')
        instance = getattr(self, 'instance', None)

        if parent is None or instance is None or not getattr(instance, 'pk', None):
            return attrs

        if parent.pk == instance.pk:
            raise serializers.ValidationError({'parent_id': '不能选择自身作为父级'})

        if parent.pk in self._get_descendant_ids(instance.pk):
            raise serializers.ValidationError({'parent_id': '不能选择自己的子级作为父级'})

        return attrs


class SysRoleMenu(models.Model):
    """
    角色菜单关联表
    """
    id = models.AutoField(primary_key=True, verbose_name='关联ID')
    role = models.ForeignKey(SysRole, on_delete=models.PROTECT, verbose_name='角色ID')
    menu = models.ForeignKey(SysMenu, on_delete=models.PROTECT, verbose_name='菜单ID')

    class Meta:
        db_table = 'sys_role_menu'
        verbose_name = '角色菜单关联表'
        verbose_name_plural = verbose_name
        unique_together = ('role', 'menu')


class SysRoleMenuSerializer(serializers.ModelSerializer):
    """
    角色菜单关联序列化器
    """
    class Meta:
        model = SysRoleMenu
        fields = '__all__'
