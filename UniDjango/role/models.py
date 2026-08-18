from django.db import models
from utils.menu_tree import build_menu_tree


# Create your models here.

class SysRole(models.Model):
    """
    角色表
    """
    id = models.AutoField(primary_key=True, verbose_name='角色ID')
    name = models.CharField(max_length=50, null=True, verbose_name='角色名称')
    code = models.CharField(max_length=50, null=True, verbose_name='角色编码')
    create_time = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')
    remark = models.CharField(max_length=200, null=True, verbose_name='备注')

    class Meta:
        db_table = 'sys_role'
        verbose_name = '角色表'
        verbose_name_plural = verbose_name


    def get_role_menus(self):
        """
        获取角色菜单（树形结构）和权限列表
        返回: (menu_tree, permission_list)
        """
        # 解决循环引入问题
        from menu.models import SysMenu, SysRoleMenu

        # 根据角色id查询出菜单id
        role_menu_qs = SysRoleMenu.objects.filter(role_id=self.id)
        menu_ids = list(role_menu_qs.values_list('menu_id', flat=True).distinct())
        # 根据菜单id查询出菜单
        menus = SysMenu.objects.filter(id__in=menu_ids).order_by('order_num', 'id')

        return build_menu_tree(menus)


class SysUserRole(models.Model):
    """
    用户角色关联表
    """ 
    id = models.AutoField(primary_key=True, verbose_name='关联ID')
    user = models.ForeignKey('user.SysUser', on_delete=models.PROTECT, verbose_name='用户ID')
    role = models.ForeignKey(SysRole, on_delete=models.PROTECT, verbose_name='角色ID')

    class Meta:
        db_table = 'sys_user_role'
        verbose_name = '用户角色关联表'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'role')


