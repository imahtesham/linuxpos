# Generated by Django 5.2.3 on 2025-06-18 10:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0001_initial'),
        ('sales', '0003_alter_sale_stock_deducted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sale',
            name='customer_name',
        ),
        migrations.AddField(
            model_name='sale',
            name='customer',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales_as_customer', to='customers.customer'),
        ),
    ]
