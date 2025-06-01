from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Panier, Utilisateur, Adresse, Commande
from django.core.exceptions import ValidationError

@receiver(post_save, sender=get_user_model())
def create_user_cart(sender, instance, created, **kwargs):
    """Crée automatiquement un panier pour chaque nouvel utilisateur."""
    if created:
        Panier.objects.create(utilisateur=instance)

# Signal pour s'assurer qu'un seul utilisateur a l'adresse de livraison par défaut
@receiver(pre_save, sender=Adresse)
def ensure_unique_default_shipping(sender, instance, **kwargs):
    if instance.is_default_shipping:
        Adresse.objects.filter(utilisateur=instance.utilisateur, is_default_shipping=True).exclude(pk=instance.pk).update(is_default_shipping=False)

# Signal pour s'assurer qu'un seul utilisateur a l'adresse de facturation par défaut
@receiver(pre_save, sender=Adresse)
def ensure_unique_default_billing(sender, instance, **kwargs):
    if instance.is_default_billing:
        Adresse.objects.filter(utilisateur=instance.utilisateur, is_default_billing=True).exclude(pk=instance.pk).update(is_default_billing=False)

# Signal pour s'assurer qu'une commande avec statut autre que 'en_attente' a au moins une ligne
@receiver(post_save, sender=Commande)
def ensure_commande_has_lignes(sender, instance, created, **kwargs):
    # Ne pas vérifier lors de la création initiale car les lignes sont ajoutées après
    if not created and instance.statut != 'en_attente':
        # Vérifier que la commande a au moins une ligne
        if not instance.lignes_commande.exists():
            # Puisque c'est un signal post_save, on ne peut pas annuler la sauvegarde
            # On peut journaliser l'erreur ou envoyer une notification
            print(f"ERREUR: La commande #{instance.id} n'a aucune ligne de commande!")





