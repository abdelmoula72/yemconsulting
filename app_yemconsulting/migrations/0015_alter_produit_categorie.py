# Generated by Django 5.2 on 2025-05-13 12:15

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0014_remove_adresse_active'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produit',
            name='categorie',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits', to='app_yemconsulting.categorie'),
        ),
    ] 