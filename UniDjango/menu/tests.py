"""menu 模块测试：菜单树构建、删除菜单时清理角色菜单关联。"""
from django.test import SimpleTestCase, TestCase

from menu.models import SysMenu, SysMenuSerializer, SysRoleMenu
from menu.views import SysMenuViewSet
from role.models import SysRole
from utils.menu_tree import build_menu_tree


class BuildMenuTreeTests(SimpleTestCase):
    def test_build_tree_and_collect_permissions(self):
        parent = SysMenu(id=1, name='p', parent_id=None, order_num=1, perms='sys:list')
        child = SysMenu(id=2, name='c', parent_id=1, order_num=1, perms='sys:add')
        roots, permissions = build_menu_tree([parent, child])

        self.assertEqual(len(roots), 1)
        self.assertEqual(roots[0]['id'], 1)
        self.assertEqual(len(roots[0]['children']), 1)
        self.assertEqual(roots[0]['children'][0]['id'], 2)
        self.assertIn('sys:list', permissions)
        self.assertIn('sys:add', permissions)

    def test_orphan_node_becomes_root(self):
        node = SysMenu(id=1, name='n', parent_id=99, order_num=1, perms=None)
        roots, _ = build_menu_tree([node])
        self.assertEqual(len(roots), 1)


class MenuDestroyTests(TestCase):
    def test_perform_destroy_clears_subtree_role_menu_links(self):
        role = SysRole.objects.create(name='r', code='r')
        parent = SysMenu.objects.create(name='parent', menu_type='C')
        child = SysMenu.objects.create(name='child', parent=parent, menu_type='F')
        SysRoleMenu.objects.create(role=role, menu=child)

        viewset = SysMenuViewSet()
        viewset.perform_destroy(parent)  # 不应抛 ProtectedError

        self.assertFalse(SysMenu.objects.filter(id__in=[parent.id, child.id]).exists())
        self.assertFalse(SysRoleMenu.objects.filter(menu_id__in=[parent.id, child.id]).exists())


class MenuCycleValidationTests(TestCase):
    def test_serializer_rejects_self_parent(self):
        menu = SysMenu.objects.create(name='self-parent', menu_type='C')

        serializer = SysMenuSerializer(menu, data={'parent_id': menu.id}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('parent_id', serializer.errors)

    def test_serializer_rejects_descendant_parent(self):
        parent = SysMenu.objects.create(name='cycle-parent', menu_type='C')
        child = SysMenu.objects.create(name='cycle-child', parent=parent, menu_type='C')
        grandchild = SysMenu.objects.create(name='cycle-grandchild', parent=child, menu_type='C')

        serializer = SysMenuSerializer(parent, data={'parent_id': grandchild.id}, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn('parent_id', serializer.errors)
