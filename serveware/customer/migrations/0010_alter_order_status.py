# Generated by Django 5.1.4 on 2025-01-15 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0009_alter_order_cart'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Canceled', 'Canceled'), ('Cooking', 'Cooking'), ('Ready_to_serve', 'Ready to Serve')], default='Pending', max_length=50),
        ),
    ]
