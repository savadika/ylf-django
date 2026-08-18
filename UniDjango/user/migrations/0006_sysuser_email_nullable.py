from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_datetime_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sysuser',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True, verbose_name='电子邮件'),
        ),
    ]
