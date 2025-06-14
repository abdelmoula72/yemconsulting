# Generated by Django 5.2 on 2025-05-19 20:02

import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0017_update_commande_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commande',
            name='panier',
        ),
        migrations.RemoveField(
            model_name='commande',
            name='traitée',
        ),
        migrations.AddField(
            model_name='commande',
            name='total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Montant total de la commande, incluant la livraison', max_digits=10),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='complement',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='nom',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='pays',
            field=models.CharField(default='Belgique', max_length=100),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='prenom',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='rue',
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name='commande',
            name='adresse_facturation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='commandes_facturation', to='app_yemconsulting.adresse'),
        ),
        migrations.AlterField(
            model_name='commande',
            name='adresse_livraison',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='commandes_livraison', to='app_yemconsulting.adresse'),
        ),
        migrations.AlterField(
            model_name='commande',
            name='livraison',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name='commande',
            name='statut',
            field=models.CharField(choices=[('en_attente', 'En attente'), ('en_cours', 'En cours de traitement'), ('livree', 'Livrée'), ('annulee', 'Annulée'), ('confirmee', 'Confirmée'), ('payee', 'Payée')], default='en_attente', max_length=50),
        ),
        migrations.AlterField(
            model_name='commande',
            name='utilisateur',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commandes', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='LigneCommande',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.PositiveIntegerField(default=1)),
                ('prix_unitaire', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Prix unitaire du produit au moment de la commande', max_digits=10)),
                ('commande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lignes_commande', to='app_yemconsulting.commande')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lignes_commande', to='app_yemconsulting.produit')),
            ],
        ),
        migrations.AddField(
            model_name='commande',
            name='produits',
            field=models.ManyToManyField(through='app_yemconsulting.LigneCommande', to='app_yemconsulting.produit'),
        ),
    ]
