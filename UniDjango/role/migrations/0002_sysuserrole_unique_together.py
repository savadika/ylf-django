from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('role', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='sysuserrole',
            unique_together={('user', 'role')},
        ),
    ]
