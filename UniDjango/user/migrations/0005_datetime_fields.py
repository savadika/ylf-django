from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_remove_sysuser_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysuser',
            name='login_date',
            field=models.DateTimeField(null=True, verbose_name='最后登录时间'),
        ),
        migrations.AlterField(
            model_name='sysuser',
            name='create_time',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='sysuser',
            name='update_time',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间'),
        ),
    ]
