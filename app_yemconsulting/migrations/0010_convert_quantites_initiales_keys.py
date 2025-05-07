from django.db import migrations

def convert_keys_to_int(apps, schema_editor):
    Commande = apps.get_model('app_yemconsulting', 'Commande')
    for commande in Commande.objects.all():
        if not commande.quantites_initiales:
            continue
        
        # Convertir les clés en entiers
        new_quantites = {}
        for key, value in commande.quantites_initiales.items():
            try:
                int_key = int(key)
                new_quantites[int_key] = value
            except (ValueError, TypeError):
                continue
        
        commande.quantites_initiales = new_quantites
        commande.save(update_fields=["quantites_initiales"])

class Migration(migrations.Migration):
    dependencies = [
        ('app_yemconsulting', '0009_quantites_initiales_rich'),
    ]
    operations = [
        migrations.RunPython(convert_keys_to_int),
    ] 