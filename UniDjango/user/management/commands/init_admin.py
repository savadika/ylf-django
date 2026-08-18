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


class Command(BaseCommand):
    help = '初始化系统：默认部门、超级管理员角色、admin 用户及通配权限'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin', help='管理员用户名（默认 admin）')
        parser.add_argument('--password', default=None, help='管理员密码，长度至少 8 位（不传则交互输入）')
        parser.add_argument('--email', default='admin@example.com', help='管理员邮箱')

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
            wildcard, _ = SysMenu.objects.get_or_create(
                name='全部权限',
                defaults={'menu_type': 'F', 'perms': '*:*:*', 'order_num': 0},
            )

            # 5. 角色绑定通配权限
            SysRoleMenu.objects.get_or_create(role=role, menu=wildcard)

            # 6. 用户绑定角色
            SysUserRole.objects.get_or_create(user=admin, role=role)

        status = '已创建' if created else '已存在（密码已更新）'
        self.stdout.write(self.style.SUCCESS(
            f'初始化完成：用户名 {username}，{status}'
        ))
