from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db.models import JSONField
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import os
from decimal import Decimal, ROUND_HALF_UP



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
        utilisateur.save(using=self._db)
        return utilisateur


# Modèle Utilisateur personnalisé

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    prenom = models.CharField(max_length=100, blank=True)
    nom = models.CharField(max_length=100)
    email = models.EmailField('Adresse email', unique=True)
    is_admin = models.BooleanField(default=False)

    class Meta:
        db_table = 'utilisateur'

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom']

    def __str__(self):
        return self.email

    @property
    def is_staff(self):
        return self.is_admin

    def save(self, *args, **kwargs):
        if self.is_admin:
            self.is_superuser = True
        super().save(*args, **kwargs)


class Adresse(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='adresses')
    prenom = models.CharField(max_length=100)
    nom = models.CharField(max_length=100)
    rue = models.CharField(max_length=255)
    complement = models.CharField(max_length=255, blank=True, null=True)
    code_postal = models.CharField(max_length=10)
    ville = models.CharField(max_length=100)
    pays = models.CharField(max_length=100, default='Belgique')
    is_default_shipping = models.BooleanField(default=False, help_text='Adresse de livraison par défaut')
    is_default_billing = models.BooleanField(default=False, help_text='Adresse de facturation par défaut')
    is_deleted = models.BooleanField(default=False, help_text='Adresse supprimée par l\'utilisateur')

    class Meta:
        db_table = 'adresse'
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
        return f"{self.prenom} {self.nom}, {self.rue}, {self.code_postal} {self.ville}, {self.pays}"




# Modèle Catégorie
class Categorie(models.Model):
    nom = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='subcategories'
    )

    class Meta:
        db_table = 'categorie'

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
        related_name="produits"
    )

    class Meta:
        db_table = 'produit'

    def __str__(self):
        return self.nom

    def get_absolute_url(self):
        return reverse('produits_par_categorie', args=[self.categorie.id])
    
    @property
    def prix_ht(self):
        return (Decimal(self.prix) / Decimal('1.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def montant_tva(self):
        return (self.prix - self.prix_ht).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)









class Panier(models.Model):
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="paniers")
    produits = models.ManyToManyField(Produit, through='LignePanier', related_name="paniers")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'panier'

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

    class Meta:
        db_table = 'ligne_panier'

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
        ('payee', 'Payée'),
    ]

    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='commandes')
    date_commande = models.DateTimeField(auto_now_add=True)
    produits = models.ManyToManyField(Produit, through='LigneCommande')
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default='en_attente')
    adresse_livraison = models.ForeignKey(
        Adresse, 
        on_delete=models.PROTECT,
        related_name='commandes_livraison',
        null=True,
        blank=True
    )
    adresse_facturation = models.ForeignKey(
        Adresse,
        on_delete=models.PROTECT,
        related_name='commandes_facturation',
        null=True,
        blank=True
    )
    prix_livraison = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Montant total de la commande, incluant la livraison'
    )
    

    class Meta:
        db_table = 'commande'

    def __str__(self):
        return f"Commande {self.id} de {self.utilisateur.nom}"

    def get_quantites(self) -> dict:
        return dict(self.lignes_commande.values_list('produit_id', 'quantite'))

    def get_total(self) -> Decimal:
        return sum(ligne.produit.prix * ligne.quantite for ligne in self.lignes_commande.all())

    def get_total_with_shipping(self) -> Decimal:
        return self.get_total() + self.prix_livraison
    
    def clean(self):
        # Validation pour s'assurer qu'une commande a au moins une ligne
        # Cette validation est appelée par les formulaires et peut être appelée manuellement
        from django.core.exceptions import ValidationError
        # Ne valider que si la commande a déjà été sauvegardée et qu'elle n'est pas en cours de création
        # Si self.pk existe, ça signifie que la commande a déjà été sauvegardée au moins une fois
        if hasattr(self, 'pk') and self.pk and not self.lignes_commande.exists():
            raise ValidationError("Une commande doit contenir au moins un produit.")
            
    def save(self, *args, **kwargs):
        # Validation supplémentaire lors de la sauvegarde
        if hasattr(self, 'pk') and self.pk and self.statut != 'en_attente':
            # Si la commande existe déjà et n'est plus en attente, 
            # vérifions qu'elle a au moins une ligne
            from django.core.exceptions import ValidationError
            if not self.lignes_commande.exists():
                raise ValidationError("Une commande confirmée doit contenir au moins un produit.")
        super().save(*args, **kwargs)


class LigneCommande(models.Model):
    commande = models.ForeignKey(
        Commande, 
        on_delete=models.CASCADE,
        related_name='lignes_commande'
    )
    produit = models.ForeignKey(
        Produit, 
        on_delete=models.PROTECT,
        related_name='lignes_commande'
    )
    quantite = models.PositiveIntegerField(default=1)
    prix_unitaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Prix unitaire du produit au moment de la commande'
    )

    class Meta:
        db_table = 'ligne_commande'

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} dans la commande {self.commande.id}"

    def save(self, *args, **kwargs):
        # Enregistrer le prix unitaire au moment de la création
        if not self.prix_unitaire:
            self.prix_unitaire = self.produit.prix
        super().save(*args, **kwargs)









