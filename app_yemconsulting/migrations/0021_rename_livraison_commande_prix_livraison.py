# Generated by Django 5.2 on 2025-05-21 09:51

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0020_sync_admin_superuser'),
    ]

    operations = [
        migrations.RenameField(
            model_name='commande',
            old_name='livraison',
            new_name='prix_livraison',
        ),
    ]
