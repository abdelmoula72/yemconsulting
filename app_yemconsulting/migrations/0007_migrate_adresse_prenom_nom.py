from django.db import migrations

def copy_user_names(apps, schema_editor):
    Adresse = apps.get_model('app_yemconsulting', 'Adresse')
    Utilisateur = apps.get_model('app_yemconsulting', 'Utilisateur')
    for adresse in Adresse.objects.all():
        user = adresse.utilisateur
        adresse.prenom = getattr(user, 'prenom', '')
        adresse.nom = getattr(user, 'nom', '')
        adresse.save()

class Migration(migrations.Migration):
    dependencies = [
        ('app_yemconsulting', '0006_adresse_nom_adresse_prenom'),
    ]
    operations = [
        migrations.RunPython(copy_user_names),
    ] 