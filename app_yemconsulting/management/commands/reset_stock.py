from django.core.management.base import BaseCommand
from app_yemconsulting.models import Produit


class Command(BaseCommand):
    help = 'Réinitialise le stock de tous les produits à la quantité initiale'

    def handle(self, *args, **kwargs):
        quantite_initiale = 100  # Quantité par défaut pour chaque produit
        produits = Produit.objects.all()
        for produit in produits:
            produit.stock = quantite_initiale
            produit.save()
        self.stdout.write(self.style.SUCCESS(f'Stocks réinitialisés à {quantite_initiale} pour tous les produits'))
