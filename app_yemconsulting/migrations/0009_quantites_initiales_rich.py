from django.db import migrations, models

def migrate_quantites_initiales(apps, schema_editor):
    Commande = apps.get_model('app_yemconsulting', 'Commande')
    Produit = apps.get_model('app_yemconsulting', 'Produit')
    for commande in Commande.objects.all():
        old = commande.quantites_initiales
        if not old:
            commande.quantites_initiales = None
            commande.save(update_fields=["quantites_initiales"])
            continue
        # Si déjà au bon format, on ne touche pas
        if isinstance(list(old.values())[0], dict):
            continue
        new = {}
        for k, qte in old.items():
            try:
                prod = Produit.objects.get(id=int(k))
                new[int(k)] = {
                    "name": prod.nom,
                    "price": float(prod.prix),
                    "quantity": qte
                }
            except Produit.DoesNotExist:
                continue
        commande.quantites_initiales = new
        commande.save(update_fields=["quantites_initiales"])

class Migration(migrations.Migration):
    dependencies = [
        ('app_yemconsulting', '0008_adresse_active_commande_address'),
    ]
    operations = [
        migrations.AlterField(
            model_name='commande',
            name='quantites_initiales',
            field=models.JSONField(default=dict, null=True, blank=True),
        ),
        migrations.RunPython(migrate_quantites_initiales),
    ] 