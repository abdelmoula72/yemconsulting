# Generated by Django 5.2 on 2025-05-06 11:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0011_commande_livraison'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commande',
            name='address',
        ),
        migrations.AddField(
            model_name='commande',
            name='adresse_facturation',
            field=models.JSONField(default=dict, help_text='Adresse de facturation au format JSON'),
        ),
        migrations.AddField(
            model_name='commande',
            name='adresse_livraison',
            field=models.JSONField(default=dict, help_text='Adresse de livraison au format JSON'),
        ),
        migrations.AlterField(
            model_name='commande',
            name='statut',
            field=models.CharField(choices=[('en_attente', 'En attente'), ('en_cours', 'En cours de traitement'), ('livree', 'Livrée'), ('annulee', 'Annulée'), ('confirmee', 'Confirmée')], default='en_attente', max_length=50),
        ),
    ]
