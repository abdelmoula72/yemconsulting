from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0016_renommer_adresse_en_rue'),
    ]

    operations = [
        # Supprimer le champ quantites_initiales
        migrations.RemoveField(
            model_name='commande',
            name='quantites_initiales',
        ),
        
        # Supprimer les champs adresse_livraison et adresse_facturation actuels (JSONField)
        migrations.RemoveField(
            model_name='commande',
            name='adresse_livraison',
        ),
        migrations.RemoveField(
            model_name='commande',
            name='adresse_facturation',
        ),
        
        # Ajouter les nouveaux champs ForeignKey
        migrations.AddField(
            model_name='commande',
            name='adresse_livraison',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='commandes_livraison',
                to='app_yemconsulting.adresse',
                help_text='Adresse de livraison'
            ),
        ),
        migrations.AddField(
            model_name='commande',
            name='adresse_facturation',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='commandes_facturation',
                to='app_yemconsulting.adresse',
                help_text='Adresse de facturation'
            ),
        ),
    ] 