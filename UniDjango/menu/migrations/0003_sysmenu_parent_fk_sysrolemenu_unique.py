import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='sysmenu',
            old_name='parent_id',
            new_name='parent',
        ),
        migrations.AlterField(
            model_name='sysmenu',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='children',
                to='menu.sysmenu',
                verbose_name='父菜单ID',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='sysrolemenu',
            unique_together={('role', 'menu')},
        ),
    ]
