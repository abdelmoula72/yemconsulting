from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0015_alter_produit_categorie'),
    ]

    operations = [
        migrations.RenameField(
            model_name='adresse',
            old_name='adresse',
            new_name='rue',
        ),
    ] 