# Generated by Django 2.1.8 on 2019-04-04 04:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('django_netjsonconfig', '0037_config_context'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='config',
            name='context',
        ),
    ]
