from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0007_alter_sysmenu_id_alter_sysmenu_remark_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysmenu',
            name='name',
            field=models.CharField(max_length=50, verbose_name='菜单名称'),
        ),
        migrations.AddConstraint(
            model_name='sysmenu',
            constraint=models.UniqueConstraint(
                fields=('parent', 'name'),
                name='uniq_menu_parent_name',
            ),
        ),
    ]
