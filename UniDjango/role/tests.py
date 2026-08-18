"""role 模块测试：删除角色时清理用户-角色、角色-菜单关联。"""
from django.test import TestCase

from menu.models import SysMenu, SysRoleMenu
from role.models import SysRole, SysUserRole
from role.views import SysRoleViewSet
from user.models import SysUser


class RoleDestroyTests(TestCase):
    def test_perform_destroy_clears_links(self):
        role = SysRole.objects.create(name='r', code='r')
        user = SysUser.objects.create(
            username='u', password='x', email='u@example.com', status=1,
        )
        menu = SysMenu.objects.create(name='m', menu_type='C')
        SysUserRole.objects.create(user=user, role=role)
        SysRoleMenu.objects.create(role=role, menu=menu)

        viewset = SysRoleViewSet()
        viewset.perform_destroy(role)  # 不应抛 ProtectedError

        self.assertFalse(SysRole.objects.filter(id=role.id).exists())
        self.assertFalse(SysUserRole.objects.filter(role_id=role.id).exists())
        self.assertFalse(SysRoleMenu.objects.filter(role_id=role.id).exists())
