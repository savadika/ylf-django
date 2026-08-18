from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0003_sysmenu_parent_fk_sysrolemenu_unique'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysmenu',
            name='create_time',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='sysmenu',
            name='update_time',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间'),
        ),
    ]
