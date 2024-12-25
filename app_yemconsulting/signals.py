from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Commande, LignePanier

@receiver(post_delete, sender=Commande)
def remettre_stock_apres_suppression_commande(sender, instance, **kwargs):
    panier = instance.panier
    for ligne in panier.lignes.all():
        produit = ligne.produit
        produit.stock += ligne.quantite
        produit.save()
