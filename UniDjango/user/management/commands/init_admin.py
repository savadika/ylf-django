"""初始化系统数据的管理命令。

一条命令完成新系统的初始引导：默认部门、超级管理员角色、admin 用户和
``*:*:*`` 通配权限。命令是幂等的（``get_or_create``），重复执行不会产生脏数据。

用法：
    python manage.py init_admin --password 'StrongPass123'
    python manage.py init_admin                    # 交互式输入密码
"""
import getpass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from department.models import SysDep
from menu.models import SysMenu, SysRoleMenu
from role.models import SysRole, SysUserRole
from user.models import SysUser


DEFAULT_MENU_TREE = [
    {
        'name': '系统管理',
        'menu_type': 'M',
        'path': '/system',
        'icon': 'el-icon-setting',
        'order_num': 1,
        'children': [
            {
                'name': '用户管理',
                'menu_type': 'C',
                'path': '/system/user',
                'component': 'user/index',
                'icon': 'el-icon-user',
                'order_num': 1,
                'buttons': [
                    ('用户列表', 'system:user:list', 1),
                    ('查看用户详情', 'system:user:query', 2),
                    ('新增用户', 'system:user:add', 3),
                    ('编辑用户', 'system:user:edit', 4),
                    ('删除用户', 'system:user:delete', 5),
                ],
            },
            {
                'name': '角色管理',
                'menu_type': 'C',
                'path': '/system/role',
                'component': 'role/index',
                'icon': 'el-icon-s-custom',
                'order_num': 2,
                'buttons': [
                    ('角色列表', 'system:role:list', 1),
                    ('查看角色详情', 'system:role:query', 2),
                    ('新增角色', 'system:role:add', 3),
                    ('编辑角色', 'system:role:edit', 4),
                    ('删除角色', 'system:role:delete', 5),
                    ('分配权限', 'system:role:permission', 6),
                ],
            },
            {
                'name': '菜单管理',
                'menu_type': 'C',
                'path': '/system/menu',
                'component': 'menu/index',
                'icon': 'el-icon-menu',
                'order_num': 3,
                'buttons': [
                    ('菜单列表', 'system:menu:list', 1),
                    ('查看菜单详情', 'system:menu:query', 2),
                    ('新增菜单', 'system:menu:add', 3),
                    ('编辑菜单', 'system:menu:edit', 4),
                    ('删除菜单', 'system:menu:delete', 5),
                ],
            },
            {
                'name': '部门管理',
                'menu_type': 'C',
                'path': '/system/department',
                'component': 'department/index',
                'icon': 'el-icon-office-building',
                'order_num': 4,
                'buttons': [
                    ('部门列表', 'system:department:list', 1),
                    ('查看部门详情', 'system:department:query', 2),
                    ('新增部门', 'system:department:add', 3),
                    ('编辑部门', 'system:department:edit', 4),
                    ('删除部门', 'system:department:delete', 5),
                ],
            },
            {
                'name': '日志管理',
                'menu_type': 'C',
                'path': '/system/log',
                'component': 'log/index',
                'icon': 'el-icon-document',
                'order_num': 5,
                'buttons': [
                    ('日志列表', 'system:log:list', 1),
                    ('查看日志详情', 'system:log:query', 2),
                ],
            },
        ],
    },
]


class Command(BaseCommand):
    help = '初始化系统：默认部门、超级管理员角色、admin 用户、默认菜单及通配权限'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='管理员用户名（默认 admin）')
        parser.add_argument('--password', default=None, help='管理员密码，长度至少 8 位（不传则交互输入）')
        parser.add_argument('--email', default='admin@example.com', help='管理员邮箱')

    def _upsert_menu(self, spec, parent=None):
        """按名称幂等创建/更新菜单节点，并递归处理子菜单和按钮。"""
        menu, _ = SysMenu.objects.get_or_create(
            name=spec['name'],
            defaults={
                'menu_type': spec.get('menu_type'),
                'path': spec.get('path'),
                'component': spec.get('component'),
                'icon': spec.get('icon'),
                'order_num': spec.get('order_num', 0),
                'perms': spec.get('perms'),
                'parent': parent,
            },
        )

        menu.menu_type = spec.get('menu_type', menu.menu_type)
        menu.path = spec.get('path', menu.path)
        menu.component = spec.get('component', menu.component)
        menu.icon = spec.get('icon', menu.icon)
        menu.order_num = spec.get('order_num', menu.order_num or 0)
        menu.perms = spec.get('perms', menu.perms)
        menu.parent = parent
        menu.save()

        created = [menu]
        for child_spec in spec.get('children', []):
            created.extend(self._upsert_menu(child_spec, parent=menu))
        for name, perms, order_num in spec.get('buttons', []):
            button_spec = {
                'name': name,
                'menu_type': 'F',
                'perms': perms,
                'order_num': order_num,
            }
            created.extend(self._upsert_menu(button_spec, parent=menu))
        return created

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        if not password:
            password = getpass.getpass('请输入管理员密码: ')
            if password != getpass.getpass('请再次确认密码: '):
                raise CommandError('两次输入的密码不一致')
        if len(password) < 8:
            raise CommandError('密码长度不能少于 8 位')

        with transaction.atomic():
            # 1. 默认部门
            department, _ = SysDep.objects.get_or_create(
                dep_name='总部', defaults={'status': 1, 'remark': '默认部门'},
            )

            # 2. 超级管理员角色
            role, _ = SysRole.objects.get_or_create(
                name='超级管理员', code='admin', defaults={'remark': '拥有全部权限'},
            )

            # 3. 管理员用户（已存在则更新密码）
            admin, created = SysUser.objects.get_or_create(
                username=username,
                defaults={'email': email, 'status': 1, 'remark': '初始管理员'},
            )
            admin.department = department
            admin.email = email
            admin.status = 1
            admin.set_password(password)
            admin.save()

            # 4. 通配权限按钮菜单
            wildcard = self._upsert_menu({
                'name': '全部权限',
                'menu_type': 'F',
                'perms': '*:*:*',
                'order_num': 0,
            })[0]

            # 5. 默认菜单树，确保空库初始化后侧边栏可用
            default_menus = []
            for root_spec in DEFAULT_MENU_TREE:
                default_menus.extend(self._upsert_menu(root_spec))

            # 6. 给超级管理员绑定通配权限和完整默认菜单
            for menu in [wildcard] + default_menus:
                SysRoleMenu.objects.get_or_create(role=role, menu=menu)

            # 7. 用户绑定角色
            SysUserRole.objects.get_or_create(user=admin, role=role)

        status = '已创建' if created else '已存在（密码已更新）'
        self.stdout.write(self.style.SUCCESS(
            f'初始化完成：用户名 {username}，{status}'
        ))
