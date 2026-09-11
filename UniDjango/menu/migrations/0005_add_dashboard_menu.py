from django.db import migrations


def add_dashboard_menu(apps, schema_editor):
    SysMenu = apps.get_model('menu', 'SysMenu')
    SysRoleMenu = apps.get_model('menu', 'SysRoleMenu')
    SysRole = apps.get_model('role', 'SysRole')

    dashboard, _ = SysMenu.objects.get_or_create(
        name='首页',
        defaults={
            'menu_type': 'C',
            'path': '/dashboard',
            'component': 'dashboard/index',
            'icon': 'dashboard',
            'order_num': 0,
            'perms': 'system:dashboard:view',
        },
    )

    # 幂等：补齐可能缺失的字段，避免旧数据或重复运行时字段不完整
    dashboard.menu_type = 'C'
    dashboard.path = '/dashboard'
    dashboard.component = 'dashboard/index'
    dashboard.icon = 'dashboard'
    dashboard.order_num = 0
    dashboard.perms = 'system:dashboard:view'
    dashboard.save()

    admin_role = SysRole.objects.filter(code='admin').first()
    if admin_role is not None:
        SysRoleMenu.objects.get_or_create(role=admin_role, menu=dashboard)


def remove_dashboard_menu(apps, schema_editor):
    SysMenu = apps.get_model('menu', 'SysMenu')
    SysRoleMenu = apps.get_model('menu', 'SysRoleMenu')

    dashboard = SysMenu.objects.filter(name='首页', perms='system:dashboard:view').first()
    if dashboard is not None:
        SysRoleMenu.objects.filter(menu=dashboard).delete()
        dashboard.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0004_datetime_fields'),
        ('role', '0003_datetime_fields'),
    ]

    operations = [
        migrations.RunPython(add_dashboard_menu, remove_dashboard_menu),
    ]
