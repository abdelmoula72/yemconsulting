from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings
from django.conf.urls.static import static 
from django.views.generic.base import RedirectView


urlpatterns = [
    # Page d'accueil = grandes catégories uniquement
    path('', views.liste_categories, name='liste_produits'),
    

    # Paiement Stripe
    path('paiement/stripe/', views.stripe_checkout, name='stripe_checkout'),
    path('paiement/stripe/success/', views.stripe_success, name='stripe_success'),


    # Navigation catégories et sous-catégories
    path('categories/', views.liste_categories, name='liste_categories'),
    path('categorie/<int:categorie_id>/', views.produits_par_categorie, name='produits_par_categorie'),
    path('produit/<int:produit_id>/', views.produit_detail, name='produit_detail'),


    # Panier et gestion
    path('ajouter_au_panier/<int:produit_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('panier/', views.afficher_panier, name='afficher_panier'),
    path('mettre_a_jour_quantite/<int:ligne_panier_id>/', views.mettre_a_jour_quantite, name='mettre_a_jour_quantite'),
    path('supprimer_article/<int:ligne_panier_id>/', views.supprimer_article, name='supprimer_article'),
    path('vider_panier/', views.vider_panier, name='vider_panier'),
    path("confirmation-panier/", views.confirmer_panier, name="confirmer_panier"),
    path("confirmer-panier/", views.confirmer_panier, name="confirmer_panier_alt"),  # URL alternative pour le JavaScript
    path('api-ajouter-adresse/', views.api_ajouter_adresse, name='api_ajouter_adresse'),
    path('update-toggle-addresses/', views.update_toggle_addresses, name='update_toggle_addresses'),

    # Commandes
    path('commande/', views.passer_commande, name='passer_commande'),
    path('confirmation_commande/<int:commande_id>/', views.confirmation_commande, name='confirmation_commande'),
    path('annuler_commande/<int:commande_id>/', views.annuler_commande, name='annuler_commande'),
    path('commandes/', views.historique_commandes, name='historique_commandes'),
    path('facture_pdf/<int:commande_id>/', views.generer_facture_pdf, name='generer_facture_pdf'),
    path('update-shipping-address/<int:adresse_id>/', views.update_shipping_address, name='update_shipping_address'),

    # Authentification et profil
    path('login/', auth_views.LoginView.as_view(redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('inscription/', views.inscription, name='inscription'),
    
    # Gestion du compte et des adresses
    path('mon-compte/', views.mon_compte, name='mon_compte'),
    path('mes-adresses/', views.mes_adresses, name='mes_adresses'),
    path('adresse/editer/<int:pk>/', views.editer_adresse, name='editer_adresse'),
    path('adresse/supprimer/<int:adresse_id>/', views.supprimer_adresse, name='supprimer_adresse'),
    path('adresse/definir-livraison/<int:pk>/', views.definir_adresse_livraison, name='definir_adresse_livraison'),
    path('adresse/definir-facturation/<int:pk>/', views.definir_adresse_facturation, name='definir_adresse_facturation'),

    # Administration
    path('admin/utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),

    # Recherche
    path('recherche/', views.rechercher_produits, name='rechercher_produits'),
    path('autocomplete_produits/', views.autocomplete_produits, name='autocomplete_produits'),
    path('suggestions/', views.suggestions_produits, name='suggestions_produits'),

    # Test
    path('test-template/', views.test_template, name='test_template'),

    path('update-billing-address/<int:adresse_id>/', views.update_billing_address, name='update_billing_address'),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)