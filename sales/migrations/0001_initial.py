# Generated by Django 5.2.3 on 2025-06-18 09:10

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('organization', '0001_initial'),
        ('products', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Sale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('customer_name', models.CharField(blank=True, help_text='Temporary, replace with FK to Customer model', max_length=255, null=True)),
                ('sale_number', models.CharField(help_text='Unique sale identifier/invoice number', max_length=50, unique=True)),
                ('sale_date', models.DateTimeField(auto_now_add=True, help_text='Timestamp when the sale was initiated/completed')),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('REFUNDED', 'Refunded')], default='PENDING', max_length=10)),
                ('sub_total', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('tax_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('grand_total', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('payment_type', models.CharField(blank=True, choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('MOBILE', 'Mobile Wallet'), ('BANK', 'Bank Transfer'), ('ACCOUNT', 'On Account (Credit)'), ('VOUCHER', 'Voucher'), ('OTHER', 'Other')], max_length=10, null=True)),
                ('amount_paid', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('change_due', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('notes', models.TextField(blank=True, null=True)),
                ('stock_deducted', models.BooleanField(default=False)),
                ('branch', models.ForeignKey(limit_choices_to={'unit_type': 'BRANCH'}, on_delete=django.db.models.deletion.PROTECT, related_name='sales', to='organization.businessunit')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_sales', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sale Transaction',
                'verbose_name_plural': 'Sale Transactions',
                'ordering': ['-sale_date'],
            },
        ),
        migrations.CreateModel(
            name='SaleItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=2, max_digits=10)),
                ('unit_price_at_sale', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_amount_item', models.DecimalField(decimal_places=2, default=0.0, max_digits=10)),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=12)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.product')),
                ('sale', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='sales.sale')),
            ],
        ),
    ]
