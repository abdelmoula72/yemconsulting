# Generated by Django 5.2 on 2025-06-03 00:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0021_rename_livraison_commande_prix_livraison'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='adresse',
            table='adresse',
        ),
        migrations.AlterModelTable(
            name='categorie',
            table='categorie',
        ),
        migrations.AlterModelTable(
            name='commande',
            table='commande',
        ),
        migrations.AlterModelTable(
            name='lignecommande',
            table='ligne_commande',
        ),
        migrations.AlterModelTable(
            name='lignepanier',
            table='ligne_panier',
        ),
        migrations.AlterModelTable(
            name='panier',
            table='panier',
        ),
        migrations.AlterModelTable(
            name='produit',
            table='produit',
        ),
        migrations.AlterModelTable(
            name='utilisateur',
            table='utilisateur',
        ),
    ]
