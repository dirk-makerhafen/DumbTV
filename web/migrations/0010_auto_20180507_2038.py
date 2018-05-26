# Generated by Django 2.0.1 on 2018-05-07 20:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0009_auto_20180505_2022'),
    ]

    operations = [
        migrations.AddField(
            model_name='upcoming',
            name='path',
            field=models.CharField(default='', max_length=10000),
        ),
        migrations.AlterField(
            model_name='upcoming',
            name='addon',
            field=models.CharField(default='', max_length=1000),
        ),
        migrations.AlterField(
            model_name='upcoming',
            name='thumbnailImage',
            field=models.CharField(default='', max_length=10000),
        ),
        migrations.AlterField(
            model_name='upcoming',
            name='title',
            field=models.CharField(default='', max_length=10000),
        ),
        migrations.AlterField(
            model_name='upcoming',
            name='url',
            field=models.CharField(default='', max_length=10000),
        ),
    ]