from django.db import models
from django.contrib.auth.hashers import make_password
from department.models import SysDep
from utils.menu_tree import build_menu_tree

# Create your models here.
class SysUser(models.Model):
    """
    用户模型
    """
    id = models.AutoField(primary_key=True, verbose_name='用户ID')
    department = models.ForeignKey(SysDep, on_delete=models.SET_NULL, null=True, verbose_name='部门')  #部门外键
    username = models.CharField(max_length=150, unique=True, verbose_name='用户名')
    password = models.CharField(max_length=128, verbose_name='密码')
    avatar = models.CharField(max_length=255, null=True, verbose_name='头像')
    email = models.EmailField(max_length=254, unique=True, null=True, blank=True, verbose_name='电子邮件')
    phone = models.CharField(max_length=15, null=True, verbose_name='电话号码')
    login_date = models.DateTimeField(null=True, verbose_name='最后登录时间')
    status = models.IntegerField(null=True, default=1, choices=[(1, '正常'), (0, '禁用')], verbose_name='状态')
    create_time = models.DateTimeField(null=True, auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(null=True, auto_now=True, verbose_name='更新时间')
    remark = models.CharField(max_length=500, null=True, verbose_name='备注')

    class Meta:
        db_table = 'sys_user'

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_active(self):
        return self.status == 1

    
    
    def get_role_menus(self):
        """
        获取用户角色菜单（树形结构）和权限列表
        返回: (menu_tree, permission_list)
        """
        # 解决循环引入问题
        from role.models import SysUserRole
        from menu.models import SysMenu, SysRoleMenu

        # 获取用户角色
        user_roles = SysUserRole.objects.filter(user_id=self.id)
        # 根据角色id查询出菜单id
        role_menu_qs = SysRoleMenu.objects.filter(role_id__in=user_roles.values_list('role_id', flat=True))
        menu_ids = list(role_menu_qs.values_list('menu_id', flat=True).distinct())
        # 根据菜单id查询出菜单
        menus = SysMenu.objects.filter(id__in=menu_ids).order_by('order_num', 'id')

        return build_menu_tree(menus, include_perms=False)
