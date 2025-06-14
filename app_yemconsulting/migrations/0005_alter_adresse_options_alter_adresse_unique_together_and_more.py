# Generated by Django 5.2 on 2025-05-04 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_yemconsulting', '0004_adresse'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='adresse',
            options={'verbose_name': 'Adresse', 'verbose_name_plural': 'Adresses'},
        ),
        migrations.AlterUniqueTogether(
            name='adresse',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='adresse',
            name='is_default_billing',
            field=models.BooleanField(default=False, help_text='Adresse de facturation par défaut'),
        ),
        migrations.AddField(
            model_name='adresse',
            name='is_default_shipping',
            field=models.BooleanField(default=False, help_text='Adresse de livraison par défaut'),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='adresse',
            field=models.CharField(max_length=250),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='code_postal',
            field=models.CharField(max_length=10),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='complement',
            field=models.CharField(blank=True, max_length=250),
        ),
        migrations.AlterField(
            model_name='adresse',
            name='pays',
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='adresse',
            constraint=models.UniqueConstraint(condition=models.Q(('is_default_shipping', True)), fields=('utilisateur', 'is_default_shipping'), name='unique_default_shipping'),
        ),
        migrations.AddConstraint(
            model_name='adresse',
            constraint=models.UniqueConstraint(condition=models.Q(('is_default_billing', True)), fields=('utilisateur', 'is_default_billing'), name='unique_default_billing'),
        ),
        migrations.RemoveField(
            model_name='adresse',
            name='is_default',
        ),
        migrations.RemoveField(
            model_name='adresse',
            name='type',
        ),
    ]
