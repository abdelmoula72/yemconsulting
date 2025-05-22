from django.db import migrations

def sync_admin_superuser(apps, schema_editor):
    """
    Synchronize is_superuser with is_admin for all existing users.
    """
    # Get the historical model
    Utilisateur = apps.get_model('app_yemconsulting', 'Utilisateur')
    
    # Update all admin users to also be superusers
    for user in Utilisateur.objects.filter(is_admin=True):
        if not user.is_superuser:
            user.is_superuser = True
            user.save(update_fields=['is_superuser'])

class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0019_adresse_is_deleted'),  # Mise à jour avec la dernière migration
    ]

    operations = [
        migrations.RunPython(sync_admin_superuser),
    ] 