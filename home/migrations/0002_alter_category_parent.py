# Generated by Django 4.2.5 on 2023-09-08 04:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(blank=True, help_text='Parent category of this category (if any).', null=True, on_delete=django.db.models.deletion.SET_NULL, to='home.category'),
        ),
    ]