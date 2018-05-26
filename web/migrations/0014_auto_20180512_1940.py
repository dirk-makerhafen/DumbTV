# Generated by Django 2.0.1 on 2018-05-12 19:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0013_auto_20180512_1901'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersetting',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='settings', to=settings.AUTH_USER_MODEL),
        ),
    ]
