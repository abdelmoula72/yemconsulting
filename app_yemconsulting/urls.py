from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static  # ← celle-ci manque chez toi


urlpatterns = [
    # Page d'accueil = grandes catégories uniquement
    path('', views.liste_categories, name='liste_produits'),


    # Navigation catégories et sous-catégories
    path('categories/', views.liste_categories, name='liste_categories'),
    path('categorie/<int:categorie_id>/', views.produits_par_categorie, name='produits_par_categorie'),

    # Panier et gestion
    path('ajouter_au_panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/', views.afficher_panier, name='afficher_panier'),
    path('mettre_a_jour_quantite/<int:ligne_panier_id>/', views.mettre_a_jour_quantite, name='mettre_a_jour_quantite'),
    path('supprimer_article/<int:ligne_panier_id>/', views.supprimer_article, name='supprimer_article'),

    # Commandes
    path('commande/', views.passer_commande, name='passer_commande'),
    path('confirmation_commande/<int:commande_id>/', views.confirmation_commande, name='confirmation_commande'),
    path('annuler_commande/<int:commande_id>/', views.annuler_commande, name='annuler_commande'),
    path('commandes/', views.historique_commandes, name='historique_commandes'),

    # Authentification et profil
    path('login/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('inscription/', views.inscription, name='inscription'),
    path('modifier_profil/', views.modifier_profil, name='modifier_profil'),

    # Administration
    path('admin/utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),

    # Recherche
    path('recherche/', views.rechercher_produits, name='rechercher_produits'),
    path('autocomplete_produits/', views.autocomplete_produits, name='autocomplete_produits'),
    path('suggestions/', views.suggestions_produits, name='suggestions_produits'),

    # Test
    path('test-template/', views.test_template, name='test_template'),
]
