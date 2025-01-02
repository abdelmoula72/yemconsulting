from django.urls import include, path
from django.shortcuts import redirect 
from . import views
from django.contrib.auth import views as auth_views


# URLs pour accéder aux différentes vues de l'application
urlpatterns = [
    path('', lambda request: redirect('liste_produits')),  # Redirection depuis l'URL racine vers la liste des produit
    path('produits/', views.liste_produits, name='liste_produits'),  # Lister les produits
    path('categorie/<int:categorie_id>/', views.produits_par_categorie, name='produits_par_categorie'),  # Afficher les produits d'une catégorie
    path('ajouter_au_panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),  # Ajouter un produit au panier
    path('panier/', views.afficher_panier, name='afficher_panier'),  # Afficher le contenu du panier
    path('commande/', views.passer_commande, name='passer_commande'),
    path('annuler_commande/<int:commande_id>/', views.annuler_commande, name='annuler_commande'),
    path('commandes/', views.historique_commandes, name='historique_commandes'),
    path('confirmation_commande/<int:commande_id>/', views.confirmation_commande, name='confirmation_commande'),
    path('modifier_profil/', views.modifier_profil, name='modifier_profil'),
    path('admin/utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), 
    path('inscription/', views.inscription, name='inscription'),
    path('mettre_a_jour_quantite/<int:ligne_panier_id>/', views.mettre_a_jour_quantite, name='mettre_a_jour_quantite'),
    path('supprimer_article/<int:ligne_panier_id>/', views.supprimer_article, name='supprimer_article'),
    path('test-template/', views.test_template, name='test_template'),
    path('recherche/', views.rechercher_produits, name='rechercher_produits'),
    path('autocomplete_produits/', views.autocomplete_produits, name='autocomplete_produits'),
    path('suggestions/', views.suggestions_produits, name='suggestions_produits'),








]
