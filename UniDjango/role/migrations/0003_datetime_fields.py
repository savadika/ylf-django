from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('role', '0002_sysuserrole_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysrole',
            name='create_time',
            field=models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间'),
        ),
        migrations.AlterField(
            model_name='sysrole',
            name='update_time',
            field=models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间'),
        ),
    ]
