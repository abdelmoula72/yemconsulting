from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Panier

@receiver(post_save, sender=get_user_model())
def create_user_cart(sender, instance, created, **kwargs):
    """Crée automatiquement un panier pour chaque nouvel utilisateur."""
    if created:
        Panier.objects.create(utilisateur=instance)





