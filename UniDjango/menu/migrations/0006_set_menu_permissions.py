from django.db import migrations


MENU_PERMISSIONS = {
    '用户管理': 'system:user:list',
    '角色管理': 'system:role:list',
    '菜单管理': 'system:menu:list',
    '部门管理': 'system:department:list',
    '日志管理': 'system:log:list',
}


def set_menu_permissions(apps, schema_editor):
    SysMenu = apps.get_model('menu', 'SysMenu')
    for name, perms in MENU_PERMISSIONS.items():
        SysMenu.objects.filter(name=name, menu_type='C').update(perms=perms)


def clear_menu_permissions(apps, schema_editor):
    SysMenu = apps.get_model('menu', 'SysMenu')
    SysMenu.objects.filter(name__in=MENU_PERMISSIONS.keys(), menu_type='C').update(perms=None)


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0005_add_dashboard_menu'),
    ]

    operations = [
        migrations.RunPython(set_menu_permissions, clear_menu_permissions),
    ]
