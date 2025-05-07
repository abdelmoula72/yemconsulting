from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db.models import JSONField
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import os
from decimal import Decimal



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
    prenom = models.CharField(max_length=100, blank=True)
    nom    = models.CharField(max_length=100)
    # ← ici, il faut absolument ce champ :
    email  = models.EmailField('Adresse email', unique=True)
    societe = models.CharField(max_length=255, blank=True)
    # Tes autres champs…
    telephone                     = models.CharField("Téléphone", max_length=20, blank=True)
    date_naissance                = models.DateField("Date de naissance", null=True, blank=True)
    adresse                       = models.CharField(max_length=255, blank=True)
    complement_adresse            = models.CharField(max_length=255, blank=True)
    code_postal                   = models.CharField(max_length=20, blank=True)
    ville                         = models.CharField(max_length=100, blank=True)
    pays                          = models.CharField(max_length=100, default="Belgique")
    # … et tous les champs facturation que tu as ajoutés …

    adresse_facturation            = models.CharField("Adresse facturation",     max_length=255, blank=True)
    complement_adresse_facturation = models.CharField("Complément facturation",   max_length=255, blank=True)
    code_postal_facturation        = models.CharField("Code postal facturation",  max_length=20,  blank=True)
    ville_facturation              = models.CharField("Ville facturation",        max_length=100, blank=True)
    pays_facturation               = models.CharField("Pays facturation",        max_length=100, default="Belgique")

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom']



class Adresse(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adresses')
    prenom = models.CharField(max_length=100, blank=True)
    nom = models.CharField(max_length=100, blank=True)
    adresse = models.CharField(max_length=250)
    complement = models.CharField(max_length=250, blank=True)
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=100)
    is_default_shipping = models.BooleanField(default=False, help_text='Adresse de livraison par défaut')
    is_default_billing = models.BooleanField(default=False, help_text='Adresse de facturation par défaut')
    active = models.BooleanField(default=True, help_text='Indique si l\'adresse est active')

    class Meta:
        verbose_name = 'Adresse'
        verbose_name_plural = 'Adresses'
        constraints = [
            models.UniqueConstraint(
                fields=['utilisateur', 'is_default_shipping'],
                condition=models.Q(is_default_shipping=True),
                name='unique_default_shipping'
            ),
            models.UniqueConstraint(
                fields=['utilisateur', 'is_default_billing'],
                condition=models.Q(is_default_billing=True),
                name='unique_default_billing'
            )
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom}, {self.adresse}, {self.code_postal} {self.ville}, {self.pays}"

    def delete(self, *args, **kwargs):
        """Soft delete : marque l'adresse comme inactive au lieu de la supprimer"""
        self.active = False
        self.save()




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
    
    @property
    def prix_ht(self):
        return round(float(self.prix) / 1.21, 2)

    @property
    def montant_tva(self):
        return round(float(self.prix) - self.prix_ht, 2)









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
        ('confirmee', 'Confirmée'),
    ]

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    panier = models.ForeignKey(Panier, on_delete=models.CASCADE)
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='en_attente')
    traitée = models.BooleanField(default=False)
    quantites_initiales = models.JSONField(default=dict, null=True, blank=True)
    adresse_livraison = models.JSONField(default=dict, help_text="Adresse de livraison au format JSON")
    adresse_facturation = models.JSONField(default=dict, help_text="Adresse de facturation au format JSON")
    livraison = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Prix de la livraison")

    def __str__(self):
        return f"Commande {self.id} de {self.utilisateur.nom}"

    def get_quantites_initiales(self):
        return self.quantites_initiales or {}

    def set_quantites_initiales(self, lignes_panier):
        self.quantites_initiales = {
            str(ligne.produit.id): {
                "quantity": ligne.quantite,
                "price": float(ligne.produit.prix),
            }
            for ligne in lignes_panier
        }
        self.save()

    def get_total_initial(self):
        return sum(
            data["price"] * data["quantity"]
            for data in self.get_quantites_initiales().values()
        )









