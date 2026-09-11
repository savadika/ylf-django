from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('role', '0004_alter_sysrole_id_alter_sysrole_remark_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysrole',
            name='name',
            field=models.CharField(max_length=50, null=True, unique=True, verbose_name='角色名称'),
        ),
        migrations.AlterField(
            model_name='sysrole',
            name='code',
            field=models.CharField(max_length=50, null=True, unique=True, verbose_name='角色编码'),
        ),
    ]
