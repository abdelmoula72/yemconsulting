from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db.models import JSONField
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import os


# Gestionnaire personnalisé pour le modèle Utilisateur
class UtilisateurManager(BaseUserManager):
    def create_user(self, email, nom, password=None):
        if not email:
            raise ValueError("L'utilisateur doit avoir une adresse email")
        utilisateur = self.model(email=self.normalize_email(email), nom=nom)
        utilisateur.set_password(password)  # Utilise 'password' ici
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, nom, password=None):
        utilisateur = self.create_user(email, nom, password)
        utilisateur.is_admin = True
        utilisateur.is_superuser = True
        utilisateur.save(using=self._db)
        return utilisateur


# Modèle Utilisateur personnalisé
class Utilisateur(AbstractBaseUser, PermissionsMixin):
    nom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    adresse = models.CharField(max_length=255, blank=True)
    date_inscription = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom']

    def __str__(self):
        return self.nom

    @property
    def is_staff(self):
        return self.is_admin



# Modèle Catégorie
class Categorie(models.Model):
    nom = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subcategories'
    )

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('produits_par_categorie', args=[self.id])





def chemin_image_produit(instance, filename):
    # Utilise le nom de la catégorie principale si elle existe, sinon la catégorie actuelle
    categorie = instance.categorie.parent.nom if instance.categorie and instance.categorie.parent else instance.categorie.nom if instance.categorie else "autre"
    # Nettoie les noms pour éviter les problèmes de chemin
    categorie = categorie.replace(" ", "_").lower()
    return os.path.join("produits", categorie, filename)


# Modèle Produit
class Produit(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    image = models.ImageField(upload_to=chemin_image_produit, null=True, blank=True)  # 📁 ImageField avec dossier par catégorie
    categorie = models.ForeignKey(
        'Categorie',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="produits"
    )

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('produits_par_categorie', args=[self.categorie.id])







class Panier(models.Model):
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="paniers")
    produits = models.ManyToManyField(Produit, through='LignePanier', related_name="paniers")
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Panier de {self.utilisateur.nom}"

    def get_total(self):
        return sum(ligne.produit.prix * ligne.quantite for ligne in self.lignes.all())

    def get_total_quantite(self):
        return sum(ligne.quantite for ligne in self.lignes.all())  # Utilise self.lignes.all()



# Modèle pour les lignes du panier, associant un produit à une quantité
class LignePanier(models.Model):
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE, related_name="lignes")
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} dans le panier de {self.panier.utilisateur.nom}"



# Modèle pour les commandes, liées à un utilisateur et un panier
class Commande(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours de traitement'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE)
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='en_attente')
    traitée = models.BooleanField(default=False)
    quantites_initiales = models.JSONField(default=dict)  # Assurez-vous d'avoir `default=dict`

    def __str__(self):
        return f"Commande {self.id} par {self.utilisateur.nom}"









