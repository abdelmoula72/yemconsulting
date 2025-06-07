from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from app_yemconsulting.models import Panier

class Command(BaseCommand):
    help = 'Crée des paniers pour les utilisateurs qui n\'en ont pas'

    def handle(self, *args, **options):
        User = get_user_model()
        users_without_cart = User.objects.filter(paniers=None)
        carts_created = 0

        for user in users_without_cart:
            Panier.objects.create(utilisateur=user)
            carts_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ {carts_created} panier(s) créé(s) avec succès!'
            )
        ) 