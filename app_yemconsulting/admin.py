from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import Commande, Produit, Categorie, Utilisateur

class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'utilisateur', 'date_commande', 'statut')  # Affiche ces champs dans la liste
    list_filter = ('statut', 'date_commande')  # Ajoute des filtres pour le statut et la date de commande
    search_fields = ('utilisateur__nom', 'utilisateur__email')  # Recherche par utilisateur (nom, email)
    
    # Ajout des actions pour les statuts
    actions = ['marquer_commande_comme_livree', 'marquer_commande_comme_attente', 'marquer_commande_comme_en_cours', 'marquer_commande_comme_annulee']

    def marquer_commande_comme_livree(self, request, queryset):
        queryset.update(statut='livree')
        self.message_user(request, "Les commandes sélectionnées ont été marquées comme livrées.")
    marquer_commande_comme_livree.short_description = "Marquer comme livrées"

    def marquer_commande_comme_attente(self, request, queryset):
        queryset.update(statut='en_attente')
        self.message_user(request, "Les commandes sélectionnées ont été remises en attente.")
    marquer_commande_comme_attente.short_description = "Marquer comme en attente"

    def marquer_commande_comme_en_cours(self, request, queryset):
        queryset.update(statut='en_cours')
        self.message_user(request, "Les commandes sélectionnées sont en cours de traitement.")
    marquer_commande_comme_en_cours.short_description = "Marquer comme en cours de traitement"

    def marquer_commande_comme_annulee(self, request, queryset):
        queryset.update(statut='annulee')
        self.message_user(request, "Les commandes sélectionnées ont été annulées.")
    marquer_commande_comme_annulee.short_description = "Marquer comme annulées"

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'nom', 'prenom', 'is_admin', 'is_staff')
    list_filter = ('is_admin', 'is_superuser')
    search_fields = ('email', 'nom', 'prenom')
    ordering = ('email',)

    fieldsets = (
        ('Informations de connexion', {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'prenom')}),
        ('Permissions', {'fields': ('is_admin', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'password1', 'password2'),
        }),
    )

admin.site.register(Commande, CommandeAdmin)
admin.site.register(Produit)
admin.site.register(Categorie)
admin.site.register(Utilisateur, CustomUserAdmin)
