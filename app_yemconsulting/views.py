import os
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from email.utils import make_msgid
from mimetypes import guess_type
import locale
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .utils.decorators import admin_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, FileResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html, strip_tags
from django.utils.formats import date_format
from django.views.decorators.http import require_http_methods, require_POST
from .models import Produit, Categorie, Panier, LignePanier, Utilisateur, Commande, Adresse, LigneCommande
from .forms import (InscriptionForm, ModifierProfilForm, DonneesPersonnellesForm, AdresseForm, ModifierMotDePasseForm)
import stripe
from email.mime.image import MIMEImage
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage          # pour les miniatures inline
import datetime as dt
from django.utils import timezone
from app_yemconsulting.utils.date_helpers import business_days_after
import mimetypes
from django.templatetags.static import static
from django.contrib.auth.forms import PasswordChangeForm
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import utils
from reportlab.pdfgen import canvas








__all__ = ["next_business_day", "business_days_after"]

def next_business_day(base=None):
    """Renvoie le prochain jour ouvrable (lundi-vendredi)."""
    base = base or timezone.localdate()
    d = base
    while d.weekday() >= 5:          # 5 = samedi, 6 = dimanche
        d += dt.timedelta(days=1)
    return d

def business_days_after(n, base=None):
    """Ajoute *n* jours ouvrables à *base* (par défaut aujourd'hui)."""
    d = next_business_day(base)
    added = 0
    while added < n:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            added += 1
    return d








@require_http_methods(["GET", "POST"])
@login_required
def confirmer_panier(request):
    utilisateur = request.user
    panier      = get_object_or_404(Panier, utilisateur=utilisateur)
    lignes_qs   = (
        LignePanier.objects
        .filter(panier=panier)
        .select_related("produit")
    )

    if not lignes_qs.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect("afficher_panier")

    # Récupérer les adresses par défaut de l'utilisateur
    adresse_livraison_defaut = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, is_deleted=False).first()
    adresse_facturation_defaut = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, is_deleted=False).first()

    # Lors du premier chargement de la page, toujours utiliser les adresses par défaut
    # ou si une adresse par défaut a été modifiée depuis la dernière visite
    if 'adresse_livraison_id' not in request.session or \
       (adresse_livraison_defaut and str(adresse_livraison_defaut.id) != request.session.get('adresse_livraison_id')):
        adresse_livraison = adresse_livraison_defaut
        if adresse_livraison:
            request.session['adresse_livraison_id'] = str(adresse_livraison.id)
    else:
        # Sinon, utiliser l'adresse de la session
        adresse_livraison_id = request.session.get('adresse_livraison_id')
        try:
            adresse_livraison = Adresse.objects.get(id=adresse_livraison_id, utilisateur=utilisateur, is_deleted=False)
        except Adresse.DoesNotExist:
            # Si l'adresse n'existe plus, revenir à l'adresse par défaut
            adresse_livraison = adresse_livraison_defaut
            if adresse_livraison:
                request.session['adresse_livraison_id'] = str(adresse_livraison.id)

    # Récupérer l'état du toggle d'adresse identique depuis la session
    toggle_facturation_identique = request.session.get('toggle_facturation_identique', False)

    # Si le toggle est activé, l'adresse de facturation est la même que l'adresse de livraison
    if toggle_facturation_identique and adresse_livraison:
        adresse_facturation = adresse_livraison
        if 'adresse_facturation_id' in request.session:
            # Synchroniser l'ID dans la session
            request.session['adresse_facturation_id'] = request.session.get('adresse_livraison_id')
        adresses_identiques = True
    else:
        # De même pour l'adresse de facturation
        if 'adresse_facturation_id' not in request.session or \
           (adresse_facturation_defaut and str(adresse_facturation_defaut.id) != request.session.get('adresse_facturation_id')):
            adresse_facturation = adresse_facturation_defaut
            if adresse_facturation:
                request.session['adresse_facturation_id'] = str(adresse_facturation.id)
        else:
            # Sinon, utiliser l'adresse de la session
            adresse_facturation_id = request.session.get('adresse_facturation_id')
            try:
                adresse_facturation = Adresse.objects.get(id=adresse_facturation_id, utilisateur=utilisateur, is_deleted=False)
            except Adresse.DoesNotExist:
                # Si l'adresse n'existe plus, revenir à l'adresse par défaut
                adresse_facturation = adresse_facturation_defaut
                if adresse_facturation:
                    request.session['adresse_facturation_id'] = str(adresse_facturation.id)

        # Vérifier si les adresses sont identiques pour l'état du toggle
        adresses_identiques = (adresse_livraison and adresse_facturation and adresse_livraison.id == adresse_facturation.id)
        # Mettre à jour la session
        request.session['toggle_facturation_identique'] = adresses_identiques
        
    # Toutes les adresses disponibles pour l'utilisateur
    adresses = Adresse.objects.filter(utilisateur=utilisateur, is_deleted=False)

    # ────────── fonctions utilitaires dates ouvrables ──────────
    def business_days_after(n):
        """
        Retourne une date en ajoutant n jours ouvrables
        (samedi et dimanche exclus).
        """
        d = timezone.localdate()
        added = 0
        while added < n:
            d += dt.timedelta(days=1)
            if d.weekday() < 5:       # 0=lundi … 4=vendredi
                added += 1
        return d

    AUJOURD_HUI    = timezone.localdate()
    DEMAIN         = business_days_after(1)
    STANDARD_DEBUT = business_days_after(2)
    STANDARD_FIN   = business_days_after(3)

    # Juste avant de formatter les dates :
    try:
        locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, "fr_FR")
        except locale.Error:
            # Sur Windows, parfois il faut "French_France"
            locale.setlocale(locale.LC_TIME, "French_France")

    # ────────── options de livraison dynamiques ──────────
    LIVRAISON_OPTIONS = {
        "standard": {
            "libelle": "Livraison standard",
            "prix":    Decimal("0.00"),
            "debut":   STANDARD_DEBUT,
            "fin":     STANDARD_FIN,
            "delai":   f"{STANDARD_DEBUT.strftime('%A %d %B')} – {STANDARD_FIN.strftime('%A %d %B')}",
        },
        "express": {
            "libelle": "Livraison Express",
            "prix":    Decimal("7.00"),
            "debut":   DEMAIN,
            "fin":     None,
            "delai":   f"{DEMAIN.strftime('%A %d %B')}",
        },
    }

    # ────────── POST : enregistre le choix puis redirige ──────────
    if request.method == "POST":
        # Récupérer le choix de livraison
        choix = request.POST.get("livraison", "standard")
        if choix not in LIVRAISON_OPTIONS:
            choix = "standard"

        # Mémoriser le choix dans la session
        request.session["livraison_select"] = choix
        request.session["livraison_prix"]   = str(LIVRAISON_OPTIONS[choix]["prix"])

        # Traiter les adresses depuis le formulaire soumis
        adresse_livraison_id = request.POST.get('adresse_livraison_id')
        adresse_facturation_id = request.POST.get('adresse_facturation_id')
        
        # Journalisation détaillée pour le débogage
        print(f"POST /confirmation-panier/ adresses du formulaire: livraison={adresse_livraison_id}, facturation={adresse_facturation_id}")
        print(f"Tous les champs du formulaire reçus: {dict(request.POST)}")
        
        # FIX: Si les adresses ne sont pas dans le formulaire, les récupérer depuis les attributs data-adresse-id
        if not adresse_livraison_id and 'adresse_livraison_id' in request.session:
            adresse_livraison_id = request.session['adresse_livraison_id']
            print(f"Récupération de l'adresse de livraison depuis la session: {adresse_livraison_id}")
            
        if not adresse_facturation_id and 'adresse_facturation_id' in request.session:
            adresse_facturation_id = request.session['adresse_facturation_id']
            print(f"Récupération de l'adresse de facturation depuis la session: {adresse_facturation_id}")
        
        # Mettre à jour les adresses dans la session si elles sont fournies
        if adresse_livraison_id:
            try:
                # Vérifier que l'adresse existe et appartient à l'utilisateur
                Adresse.objects.get(id=adresse_livraison_id, utilisateur=utilisateur, is_deleted=False)
                request.session['adresse_livraison_id'] = str(adresse_livraison_id)
                print(f"Adresse de livraison mise à jour dans la session: {adresse_livraison_id}")
            except (Adresse.DoesNotExist, ValueError):
                print(f"Adresse de livraison invalide: {adresse_livraison_id}")
        
        if adresse_facturation_id:
            try:
                # Vérifier que l'adresse existe et appartient à l'utilisateur
                Adresse.objects.get(id=adresse_facturation_id, utilisateur=utilisateur, is_deleted=False)
                request.session['adresse_facturation_id'] = str(adresse_facturation_id)
                print(f"Adresse de facturation mise à jour dans la session: {adresse_facturation_id}")
            except (Adresse.DoesNotExist, ValueError):
                print(f"Adresse de facturation invalide: {adresse_facturation_id}")

        # Vérifier que les adresses sont bien enregistrées dans la session
        print(f"Session avant redirection: livraison={request.session.get('adresse_livraison_id')}, facturation={request.session.get('adresse_facturation_id')}")

        return redirect("stripe_checkout")

    # ────────── GET : prépare l'affichage ──────────
    livraison_select = request.session.get("livraison_select", "standard")
    livraison_info   = LIVRAISON_OPTIONS[livraison_select]

    lignes      = []
    total = Decimal("0.00")
    total_ht    = Decimal("0.00")
    total_tva   = Decimal("0.00")
    total_articles = 0

    for lp in lignes_qs:
        prod = lp.produit
        # Convertir le prix à Decimal et calculer correctement en conservant le prix exact
        prix_ttc = prod.prix
        # Calculer le prix HT de manière exacte (2 décimales)
        prix_ht = (prix_ttc / Decimal('1.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # Calculer la TVA par différence pour s'assurer que la somme égale le prix TTC
        montant_tva = (prix_ttc - prix_ht).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        img_url = prod.image.url if prod.image else static("default.jpg")
        
        sous_total = (prix_ttc * lp.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total_ht = (prix_ht * lp.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total_tva = (montant_tva * lp.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_articles += lp.quantite
        
        lignes.append({
            "image_url": img_url,
            "nom"      : prod.nom,
            "quantite" : lp.quantite,
            "prix"     : prix_ttc,
            "prix_ht"  : prix_ht,
            "montant_tva": montant_tva,
            "sous_total": sous_total,
        })
        
        total += sous_total
        total_ht += sous_total_ht
        total_tva += sous_total_tva

    # S'assurer que tous les totaux sont arrondis à 2 décimales
    total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_ht = total_ht.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_tva = total_tva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Calculer le total TTC avec livraison
    total_ttc = total
    total_avec_livraison = total + livraison_info["prix"]

    form = ModifierProfilForm(instance=request.user)

    context = {
        "utilisateur"      : utilisateur,
        "lignes"           : lignes,
        "sous_total"       : total,
        "total_ht"        : total_ht,
        "total_tva"       : total_tva,
        "total_ttc"        : total_ttc,
        "total_avec_livraison": total_avec_livraison,
        "livraisons"       : LIVRAISON_OPTIONS,
        "livraison_select" : livraison_select,
        "livraison"        : livraison_info,
        "form"             : form,
        "adresse_livraison": adresse_livraison,
        "adresse_facturation": adresse_facturation,
        "adresses"         : adresses,
        "toggle_facturation_identique": adresses_identiques,
    }
    return render(request, "panier/confirmation_panier.html", context)








stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def stripe_checkout(request):
    utilisateur = request.user
    
    # Vérifier si on paye une commande existante ou le panier
    commande_id = request.POST.get('commande_id')
    
    if commande_id:
        # Paiement d'une commande existante
        commande = get_object_or_404(Commande, id=commande_id, utilisateur=utilisateur, statut='confirmee')
        
        # Stocker l'ID de la commande dans la session pour la retrouver après
        request.session['commande_id_a_payer'] = commande_id
        
        line_items = []
        
        # Articles de la commande
        for ligne in commande.lignes_commande.all():
            p = ligne.produit
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": p.nom},
                    "unit_amount": int(ligne.prix_unitaire * 100),  # centimes
                },
                "quantity": ligne.quantite,
            })
        
        # Frais de livraison
        if commande.prix_livraison > 0:
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": "Frais de livraison"},
                    "unit_amount": int(commande.prix_livraison * 100),
                },
                "quantity": 1,
            })
    else:
        # Paiement du panier actuel
        panier = get_object_or_404(Panier, utilisateur=utilisateur)
        lignes = LignePanier.objects.filter(panier=panier)

        if not lignes.exists():
            messages.error(request, "Votre panier est vide.")
            return redirect("afficher_panier")

        # Debug: afficher les adresses stockées en session avant la création de session Stripe
        print(f"Adresses avant Stripe: livraison={request.session.get('adresse_livraison_id')}, facturation={request.session.get('adresse_facturation_id')}")

        line_items = []

        # 🟦 articles du panier
        for ligne in lignes:
            p = ligne.produit
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": p.nom},
                    "unit_amount": int(p.prix * 100),  # centimes
                },
                "quantity": ligne.quantite,
            })

        # 🟪 frais de livraison éventuels
        livraison_prix = Decimal(request.session.get("livraison_prix", "0.00"))
        if livraison_prix > 0:
            line_items.append({
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": "Frais de livraison"},
                    "unit_amount": int(livraison_prix * 100),
                },
                "quantity": 1,
            })

    # création de la Session Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(reverse("stripe_success")),
        cancel_url=request.build_absolute_uri(
            reverse("confirmation_commande", args=[commande_id]) if commande_id 
            else reverse("afficher_panier")
        ),
    )

    return redirect(session.url, code=303)



@login_required
def stripe_success(request):
    # 💳 Indiquer que le paiement a été effectué via Stripe
    request.session['methode_paiement'] = 'Stripe'
    
    # Vérifier si on payait une commande existante
    commande_id_a_payer = request.session.pop('commande_id_a_payer', None)
    
    if commande_id_a_payer:
        # Mettre à jour le statut de la commande existante
        try:
            commande = Commande.objects.get(id=commande_id_a_payer, utilisateur=request.user)
            commande.statut = 'payee'
            commande.save()
            messages.success(request, "Paiement effectué avec succès!")
            return redirect('confirmation_commande', commande_id=commande_id_a_payer)
        except Commande.DoesNotExist:
            messages.error(request, "Commande introuvable.")
            return redirect('historique_commandes')
    else:
        # Indiquer que le paiement a réussi pour la création d'une nouvelle commande
        request.session['paiement_reussi'] = True
        
        # Debug: Afficher les adresses en session après paiement réussi
        print(f"Session après paiement Stripe réussi: livraison_id={request.session.get('adresse_livraison_id')}, facturation_id={request.session.get('adresse_facturation_id')}")

        # ⏩ Rediriger vers la création de commande
        return redirect('passer_commande')





# Page principale : grandes catégories
def liste_categories(request):
    categories = Categorie.objects.filter(parent__isnull=True)
    return render(request, 'produits/liste_produits.html', {
        'categories': categories
    })




# Affichage des sous-catégories ou des produits
def produits_par_categorie(request, categorie_id):
    categorie = get_object_or_404(Categorie, id=categorie_id)
    sous_categories = categorie.subcategories.all()

    if sous_categories.exists():
        return render(request, 'produits/sous_categorie.html', {
            'categorie': categorie,
            'sous_categories': sous_categories
        })

    produits = Produit.objects.filter(categorie=categorie)
    return render(request, 'produits/liste.html', {
        'produits': produits,
        'categorie': categorie,
    })




def produit_detail(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    return render(request, 'produits/produit_detail.html', {'produit': produit})





@login_required
def ajouter_au_panier(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    quantite = int(request.POST.get('quantite', 1))

    # Vérifier simplement si le stock est suffisant, sans le décrémenter
    if produit.stock < quantite:
        return JsonResponse({'success': False, 'message': f"Stock insuffisant ({produit.stock} restants)."}, status=400)

    utilisateur = request.user
    panier, created = Panier.objects.get_or_create(utilisateur=utilisateur)
    ligne_panier, created = LignePanier.objects.get_or_create(panier=panier, produit=produit)

    # Mettre à jour la quantité sans décrémenter le stock
    if not created:
        ligne_panier.quantite += quantite
    else:
        ligne_panier.quantite = quantite
    ligne_panier.save()

    total_articles = sum(ligne.quantite for ligne in LignePanier.objects.filter(panier=panier))

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f"{quantite} {produit.nom} ajouté(s) au panier.",
            'total_quantite': total_articles
        })

    messages.success(request, f"{quantite} {produit.nom} ajouté(s) au panier.")
    return redirect('liste_produits')

















@login_required
def afficher_panier(request):
    utilisateur = get_object_or_404(Utilisateur, email=request.user.email)
    panier, created = Panier.objects.get_or_create(utilisateur=utilisateur)

    lignes_commande = []
    total = Decimal("0.00")
    total_ht = Decimal("0.00")
    total_tva = Decimal("0.00")
    total_articles = 0

    for ligne in (
        LignePanier.objects
        .select_related("produit")
        .filter(panier=panier)
    ):
        prod = ligne.produit
        prix_ttc = prod.prix
        prix_ht = (prix_ttc / Decimal('1.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        montant_tva = (prix_ttc - prix_ht).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        img_url = prod.image.url if prod.image else static("default.jpg")

        sous_total = (prix_ttc * ligne.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total_ht = (prix_ht * ligne.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total_tva = (montant_tva * ligne.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_articles += ligne.quantite

        lignes_commande.append({
            "id"        : ligne.id,
            "nom"       : prod.nom,
            "prix"      : prix_ttc,
            "prix_ht"   : prix_ht,
            "montant_tva": montant_tva,
            "quantite"  : ligne.quantite,
            "sous_total": sous_total,
            "img_url"   : img_url,
            "stock"     : prod.stock  # Ajout du stock disponible
        })

        total += sous_total
        total_ht += sous_total_ht
        total_tva += sous_total_tva
    
    # Arrondir les totaux finaux
    total = total.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_ht = total_ht.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) 
    total_tva = total_tva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return render(
        request,
        "panier/afficher_panier.html",
        {
            "lignes_commande": lignes_commande,
            "total": total,
            "total_ht": total_ht,
            "total_tva": total_tva,
            "total_articles": total_articles
        }
    )













@login_required
def passer_commande(request):
    utilisateur = get_object_or_404(Utilisateur, email=request.user.email)
    panier      = get_object_or_404(Panier, utilisateur=utilisateur)
    methode_paiement = request.session.pop("methode_paiement", "Inconnu")

    # Debugging: Afficher les valeurs en session au début de la fonction
    print(f"====== CRÉATION DE COMMANDE ======")
    print(f"Session adresse_livraison_id: {request.session.get('adresse_livraison_id')}")
    print(f"Session adresse_facturation_id: {request.session.get('adresse_facturation_id')}")
    print(f"Toggle facturation identique: {request.session.get('toggle_facturation_identique', False)}")

    lignes_panier = (
        LignePanier.objects
        .filter(panier=panier)
        .select_related("produit")
    )
    if not lignes_panier.exists():
        return JsonResponse(
            {"success": False, "message": "Votre panier est vide."},
            status=400
        )

    # Récupérer l'adresse de livraison de la session
    adresse_livraison_id = request.session.get('adresse_livraison_id')
    print(f"Adresse de livraison ID dans session: {adresse_livraison_id}")
    
    # Si l'ID existe dans la session, récupérer cette adresse spécifique
    if adresse_livraison_id:
        try:
            adresse_livraison = Adresse.objects.get(id=adresse_livraison_id, utilisateur=utilisateur, is_deleted=False)
            print(f"Utilisation de l'adresse de livraison sélectionnée: {adresse_livraison.id} - {adresse_livraison}")
        except (Adresse.DoesNotExist, ValueError):
            print(f"L'adresse de livraison ID {adresse_livraison_id} n'existe pas ou n'est pas active")
            # Fallback à l'adresse par défaut
            adresse_livraison = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, is_deleted=False).first()
            if adresse_livraison:
                adresse_livraison_id = adresse_livraison.id
                request.session['adresse_livraison_id'] = str(adresse_livraison.id)
                print(f"Fallback à l'adresse de livraison par défaut: {adresse_livraison.id}")
            else:
                print("Aucune adresse de livraison trouvée")
                return JsonResponse(
                    {"success": False, "message": "Aucune adresse de livraison valide trouvée."},
                    status=400
                )
    else:
        # Aucune adresse en session, utiliser l'adresse par défaut
        adresse_livraison = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, is_deleted=False).first()
        if adresse_livraison:
            adresse_livraison_id = adresse_livraison.id
            request.session['adresse_livraison_id'] = str(adresse_livraison.id)
            print(f"Utilisation de l'adresse de livraison par défaut: {adresse_livraison.id}")
        else:
            print("Aucune adresse de livraison par défaut trouvée")
            return JsonResponse(
                {"success": False, "message": "Aucune adresse de livraison sélectionnée."},
                status=400
            )

    # Récupérer l'adresse de facturation de la session
    adresse_facturation_id = request.session.get('adresse_facturation_id')
    toggle_facturation_identique = request.session.get('toggle_facturation_identique', False)
    print(f"Adresse de facturation ID dans session: {adresse_facturation_id}")
    print(f"Toggle facturation identique: {toggle_facturation_identique}")
    
    # CORRECTION: Ne pas utiliser le toggle pour écraser l'adresse de facturation si elle a été explicitement choisie
    # Si une adresse de facturation est spécifiée, l'utiliser indépendamment du toggle
    if adresse_facturation_id:
        try:
            adresse_facturation = Adresse.objects.get(id=adresse_facturation_id, utilisateur=utilisateur, is_deleted=False)
            print(f"Utilisation de l'adresse de facturation sélectionnée: {adresse_facturation.id} - {adresse_facturation}")
        except (Adresse.DoesNotExist, ValueError):
            print(f"L'adresse de facturation ID {adresse_facturation_id} n'existe pas ou n'est pas active")
            # Fallback à l'adresse par défaut ou à l'adresse de livraison
            adresse_facturation_defaut = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, is_deleted=False).first()
            if adresse_facturation_defaut:
                adresse_facturation = adresse_facturation_defaut
                print(f"Fallback à l'adresse de facturation par défaut: {adresse_facturation.id}")
            else:
                print(f"Pas d'adresse de facturation trouvée, utilisation de l'adresse de livraison: {adresse_livraison.id}")
                adresse_facturation = adresse_livraison
    else:
        # Si pas d'adresse de facturation en session, utiliser le comportement du toggle
        if toggle_facturation_identique:
            print(f"Toggle activé et pas d'adresse de facturation spécifiée: utilisation de l'adresse de livraison")
            adresse_facturation = adresse_livraison
        else:
            # Aucune adresse en session, utiliser l'adresse par défaut ou l'adresse de livraison
            adresse_facturation = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, is_deleted=False).first()
            if adresse_facturation:
                print(f"Utilisation de l'adresse de facturation par défaut: {adresse_facturation.id}")
            else:
                print(f"Aucune adresse de facturation par défaut, utilisation de l'adresse de livraison: {adresse_livraison.id}")
                adresse_facturation = adresse_livraison

    # Vérifier si le paiement a été effectué avec succès
    paiement_reussi = request.session.pop("paiement_reussi", False)
    statut_commande = "payee" if paiement_reussi else "confirmee"
    
    # ────────── création de la commande ──────────
    livraison_prix = Decimal(request.session.pop("livraison_prix", "0.00"))
    
    # Utiliser directement les instances d'adresses
    commande = Commande.objects.create(
        utilisateur=utilisateur,
        statut=statut_commande,
        adresse_livraison=adresse_livraison,
        adresse_facturation=adresse_facturation,
        prix_livraison=livraison_prix
    )
    
    print(f"Commande créée avec adresse_livraison_id={adresse_livraison.id}, adresse_facturation_id={adresse_facturation.id}")

    # Créer les lignes de commande à partir des lignes de panier
    for ligne in lignes_panier:
        LigneCommande.objects.create(
            commande=commande,
            produit=ligne.produit,
            quantite=ligne.quantite,
            prix_unitaire=ligne.produit.prix
        )
    
    # Calcul du total et sauvegarde
    commande.total = commande.get_total_with_shipping()
    commande.save(update_fields=['total'])
    
    # ────────── gestion du stock ──────────
    # Ne décrémenter le stock que si le paiement a été confirmé
    if paiement_reussi:
        produits_alerte_stock = set()
        for ligne in lignes_panier:
            prod = ligne.produit
            if prod.stock >= ligne.quantite:
                prod.stock -= ligne.quantite
                prod.save(update_fields=["stock"])
                if prod.stock <= 15:
                    produits_alerte_stock.add(prod)

    # ────────── totaux (HT / TVA / TTC) ──────────
    total_ttc = commande.get_total()
    coeff_tva = Decimal("1.21")
    total_ht = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)
    
    # ────────── préparation des lignes pour l'e-mail ──────────
    email_lignes = []
    images_a_attacher = []        # [(cid, path), …]

    for ligne in lignes_panier:
        prod = ligne.produit

        # image locale (MEDIA) ou fallback STATIC
        if prod.image and prod.image.name:
            img_path = prod.image.path
        else:
            img_path = staticfiles_storage.path("default.jpg")

        cid = make_msgid(domain="yemconsulting.local")
        email_lignes.append({
            "nom"      : prod.nom,
            "quantite" : ligne.quantite,
            "prix"     : prod.prix,
            "img_cid"  : cid[1:-1],  # sans < >
        })
        images_a_attacher.append((cid, img_path))

    # ────────── dates de livraison « ouvrables » ──────────
    locale.setlocale(locale.LC_TIME, "")   # on garde la locale système

    std_1 = business_days_after(2)
    std_2 = business_days_after(3)
    express = business_days_after(1)

    livraison_debut = business_days_after(2)
    livraison_fin   = business_days_after(3)
    livraison_express = express.strftime("%a, %d %b %Y")

    # ────────── contexte mail ──────────
    ctx = {
        "utilisateur"     : utilisateur,
        "commande"        : commande,
        "lignes"          : email_lignes,
        "total_ht"        : total_ht,
        "total_tva"       : total_tva,
        "total_ttc"       : total_ttc + livraison_prix,  # Total TTC incluant la livraison
        "methode_paiement": methode_paiement,
        "url_commande"    : request.build_absolute_uri( reverse("confirmation_commande", args=[commande.id]) ),
        "livraison_debut": livraison_debut.strftime("%a %d %b %Y"),
        "livraison_fin"  : livraison_fin.strftime("%a %d %b %Y"),
        "livraison_express": f"{express.strftime('%a')}, {express.day} {express.strftime('%b %Y')}",
        "livraison_prix"  : livraison_prix,
        "adresse_livraison": adresse_livraison,
        "adresse_facturation": adresse_facturation,
    }

    html_body = render_to_string("emails/confirmation_commande.html", ctx)
    text_body = render_to_string("emails/confirmation_commande.txt", ctx)

    # ────────── envoi du mail avec facture en pièce jointe ──────────
    # Générer le PDF de la facture pour l'attacher au mail
    # Créer un tampon en mémoire pour le PDF
    pdf_buffer = io.BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        title=f"Facture {commande.id}"
    )
    
    # Conteneur pour les éléments du PDF
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(
        name='InvoiceTitle', 
        parent=styles['Heading1'], 
        alignment=1,
        spaceAfter=20
    ))
    
    # Classe personnalisée pour positionner le logo en haut à gauche sans tenir compte des marges
    class LogoCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self.logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo-header1.jpg')
            
        def showPage(self):
            if os.path.exists(self.logo_path):
                self.saveState()
                img = utils.ImageReader(self.logo_path)
                # Positionner le logo dans le coin supérieur gauche
                self.drawImage(img, 20, A4[1] - 100, width=180, height=96)
                self.restoreState()
            canvas.Canvas.showPage(self)
    
    # Ajouter le logo dans l'en-tête (maintenant géré par le canvas personnalisé)
    # Le logo sera ajouté par la classe LogoCanvas, on n'a plus besoin de l'ajouter ici
    
    # Titre
    elements.append(Paragraph(f"FACTURE N° {commande.id}", styles['InvoiceTitle']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Date et informations
    elements.append(Paragraph(f"Date: {commande.date_commande.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Référence: CMD-{commande.id}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Informations client et adresses
    elements.append(Paragraph("Client:", styles['Heading3']))
    elements.append(Paragraph(f"{commande.utilisateur.prenom} {commande.utilisateur.nom}", styles['Normal']))
    elements.append(Paragraph(f"Email: {commande.utilisateur.email}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Adresse de facturation
    elements.append(Paragraph("Adresse de facturation:", styles['Heading4']))
    elements.append(Paragraph(f"{commande.adresse_facturation.prenom} {commande.adresse_facturation.nom}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.rue}", styles['Normal']))
    if commande.adresse_facturation.complement:
        elements.append(Paragraph(f"{commande.adresse_facturation.complement}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.code_postal} {commande.adresse_facturation.ville}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.pays}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Adresse de livraison
    elements.append(Paragraph("Adresse de livraison:", styles['Heading4']))
    elements.append(Paragraph(f"{commande.adresse_livraison.prenom} {commande.adresse_livraison.nom}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.rue}", styles['Normal']))
    if commande.adresse_livraison.complement:
        elements.append(Paragraph(f"{commande.adresse_livraison.complement}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.code_postal} {commande.adresse_livraison.ville}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.pays}", styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Détails des produits
    # En-têtes
    data = [["Produit", "Quantité", "Prix unitaire HT", "Total HT"]]
    
    # Calcul des totaux
    total_ttc = commande.get_total()
    coeff_tva = Decimal("1.21")
    total_ht = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)
    livraison_prix = commande.prix_livraison
    
    # Récupérer les détails des produits
    for ligne in commande.lignes_commande.all():
        produit = ligne.produit
        quantite = ligne.quantite
        prix_ttc = ligne.prix_unitaire
        prix_ht = prix_ttc / coeff_tva
        sous_total_ht = prix_ht * quantite
        
        data.append([
            produit.nom,
            str(quantite),
            f"{prix_ht:.2f} €",
            f"{sous_total_ht:.2f} €"
        ])
    
    # Créer la table
    table = Table(data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Totaux
    data_totaux = [
        ["Sous-total HT", f"{total_ht:.2f} €"],
        ["TVA (21%)", f"{total_tva:.2f} €"],
        ["Total TTC", f"{total_ttc:.2f} €"],
        ["Livraison", f"{livraison_prix:.2f} €" if livraison_prix > 0 else "Gratuite"],
        ["Total TTC avec livraison", f"{total_ttc + livraison_prix:.2f} €"],
    ]
    
    table_totaux = Table(data_totaux, colWidths=[12*cm, 4*cm])
    table_totaux.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table_totaux)
    
    # Notes
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Merci pour votre achat chez YemTech Pro !", styles['Center']))
    elements.append(Paragraph("Cette facture a été générée automatiquement.", styles['Center']))
    
    # Construire le PDF avec le canvas personnalisé
    doc.build(elements, canvasmaker=LogoCanvas)
    
    # Positionner le curseur au début du buffer
    pdf_buffer.seek(0)
    
    # ────────── mail + miniatures inline ──────────
    mail = EmailMultiAlternatives(
        subject="Confirmation de votre commande",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[utilisateur.email],
    )
    mail.attach_alternative(html_body, "text/html")

    # Attacher la facture en pièce jointe
    mail.attach(f"facture_{commande.id}.pdf", pdf_buffer.getvalue(), 'application/pdf')

    for cid, path in images_a_attacher:
        try:
            with open(path, "rb") as fp:
                main, sub = mimetypes.guess_type(path)[0].split("/")
                img = MIMEImage(fp.read(), _subtype=sub)
                img.add_header("Content-ID", cid)
                img.add_header("Content-Disposition", "inline",
                               filename=os.path.basename(path))
                mail.attach(img)
        except FileNotFoundError:
            pass

    mail.send(fail_silently=False)

    # ────────── alerte stock bas (inchangée) ──────────
    if produits_alerte_stock:
        alertes_txt = "\n".join(
            f"{p.nom} ({p.stock} restants)" for p in produits_alerte_stock
        )
        corps_html = "<br>".join(alertes_txt.splitlines())
        alert_mail = EmailMultiAlternatives(
            "⚠️ Alerte Stock Bas",
            f"Attention !\n\n{alertes_txt}",
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_ADMIN_EMAIL],
        )
        alert_mail.attach_alternative(
            f"<strong>Attention&nbsp;!</strong><br>{corps_html}", "text/html"
        )
        alert_mail.send()

    # ────────── on vide le panier ──────────
    lignes_panier.delete()
    
    # ────────── nettoyer les informations de session ──────────
    # On supprime les adresses de la session une fois la commande créée
    if 'adresse_livraison_id' in request.session:
        del request.session['adresse_livraison_id']
    if 'adresse_facturation_id' in request.session:
        del request.session['adresse_facturation_id']
    print("Session nettoyée après création de commande réussie")

    # ────────── réponse / redirection ──────────
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True,
                             "message": "Commande passée avec succès."})

    messages.success(request, f"Commande passée avec succès ({methode_paiement}).")
    return redirect("confirmation_commande", commande_id=commande.id)









from django.shortcuts import render

def test_template(request):
    return render(request, 'test_template.html')  # Assure-toi d'avoir ce fichier HTML












@login_required
def confirmation_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, utilisateur=request.user)

    # Récupérer les lignes de commande
    lignes_commande = []
    total_ht = Decimal('0.00')

    for ligne in commande.lignes_commande.all().select_related('produit'):
        produit = ligne.produit
        prix_ttc = ligne.prix_unitaire
        prix_ht = (prix_ttc / Decimal('1.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        montant_tva = (prix_ttc - prix_ht).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total_ht = (prix_ht * ligne.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sous_total = (prix_ttc * ligne.quantite).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # calcul de l'URL de la miniature
        if produit.image and produit.image.url:
            img_url = produit.image.url
        else:
            img_url = static('default.jpg')

        lignes_commande.append({
            'produit': produit,
            'quantite': ligne.quantite,
            'prix': prix_ttc,
            'prix_ht': prix_ht,
            'montant_tva': montant_tva,
            'sous_total_ht': sous_total_ht,
            'sous_total': sous_total,
            'image_url': img_url,
        })
        total_ht += sous_total_ht

    # Calculer la TVA et les totaux
    total_ht = total_ht.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_tva = (total_ht * Decimal('0.21')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_ttc = (total_ht + total_tva).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Ajouter le prix de livraison au total TTC
    total_avec_livraison = (total_ttc + commande.prix_livraison).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return render(request, 'commande/confirmation_commande.html', {
        'commande': commande,
        'lignes_commande': lignes_commande,
        'total_ht': total_ht,
        'total_tva': total_tva,
        'total_ttc': total_ttc,
        'total_avec_livraison': total_avec_livraison,
        'adresse_livraison': commande.adresse_livraison,
        'adresse_facturation': commande.adresse_facturation,
    })









@login_required
def historique_commandes(request):
    commandes = Commande.objects.filter(utilisateur=request.user).order_by('-date_commande')
    return render(request, 'commande/historique_commandes.html', {
        'commandes': commandes
    })





@login_required
def annuler_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, utilisateur=request.user)

    if commande.statut != 'en_attente':
        messages.error(request, "Cette commande ne peut plus être annulée.")
        return redirect('historique_commandes')

    # Restaurer le stock en utilisant les lignes de commande
    with transaction.atomic():  
        for ligne in commande.lignes_commande.select_for_update().all():
            produit = Produit.objects.select_for_update().get(id=ligne.produit.id)
            produit.stock += ligne.quantite
            produit.save()

        commande.statut = 'annulee'
        commande.save()

    messages.success(request, "Commande annulée avec succès.")
    return redirect('historique_commandes')










def inscription(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('liste_produits')
    else:
        form = InscriptionForm()

    # Ajout des classes d'erreur pour chaque champ
    is_invalid_prenom = "is-invalid" if form['prenom'].errors else ""
    is_invalid_nom = "is-invalid" if form['nom'].errors else ""
    is_invalid_email = "is-invalid" if form['email'].errors else ""
    is_invalid_password1 = "is-invalid" if form['password1'].errors else ""
    is_invalid_password2 = "is-invalid" if form['password2'].errors else ""

    return render(request, 'registration/inscription.html', {
        'form': form,
        'is_invalid_prenom': is_invalid_prenom,
        'is_invalid_nom': is_invalid_nom,
        'is_invalid_email': is_invalid_email,
        'is_invalid_password1': is_invalid_password1,
        'is_invalid_password2': is_invalid_password2,
    })




@login_required
def mes_adresses(request):
    user = request.user
    edit_type = request.GET.get('edit')
    pk = request.GET.get('pk')
    next_url = request.GET.get('next')

    # Si aucune adresse n'existe, rediriger vers ajout avec les deux cases pré-cochées
    if user.adresses.filter(is_deleted=False).count() == 0 and not edit_type:
        return editer_adresse(request, first_address=True)

    # Si on vient de la confirmation panier et pas de paramètre edit, rediriger vers l'adresse de livraison par défaut
    if next_url and not edit_type:
        adresse_livraison = user.adresses.filter(is_default_shipping=True, is_deleted=False).first()
        if adresse_livraison:
            url = f"{request.path}?edit=shipping&pk={adresse_livraison.pk}"
            if next_url:
                url += f"&next={next_url}"
            return redirect(url)

    if edit_type in ['shipping', 'billing']:
        return editer_adresse(request, pk=pk)

    # Récupère toutes les adresses non supprimées
    adresses = user.adresses.filter(is_deleted=False)
    return render(request, 'utilisateur/mes_adresses_list.html', {
        'adresses': adresses,
    })

@login_required
def editer_adresse(request, pk=None, first_address=False):
    user = request.user

    # Choix de l'instance (modification vs création)
    if pk:
        adresse = get_object_or_404(Adresse, pk=pk, utilisateur=user, is_deleted=False)
    else:
        adresse = Adresse(utilisateur=user)

    if request.method == 'POST':
        form = AdresseForm(request.POST, instance=adresse, user=user)
        if form.is_valid():
            cd = form.cleaned_data
            if pk:
                adresse = form.save(commit=False)
                if cd.get('is_default_shipping'):
                    Adresse.objects.filter(utilisateur=user, is_default_shipping=True).exclude(pk=adresse.pk).update(is_default_shipping=False)
                if cd.get('is_default_billing'):
                    Adresse.objects.filter(utilisateur=user, is_default_billing=True).exclude(pk=adresse.pk).update(is_default_billing=False)
            else:
                adresse = form.save(commit=False)
                adresse.utilisateur = user
                if first_address:
                    adresse.is_default_shipping = True
                    adresse.is_default_billing = True
                else:
                    if cd.get('is_default_shipping'):
                        Adresse.objects.filter(utilisateur=user, is_default_shipping=True).update(is_default_shipping=False)
                    if cd.get('is_default_billing'):
                        Adresse.objects.filter(utilisateur=user, is_default_billing=True).update(is_default_billing=False)
            
            adresse.save()
            messages.success(request, 'Adresse enregistrée avec succès.')
            return redirect('mes_adresses')
    else:
        form = AdresseForm(instance=adresse, user=user)
        if first_address:
            form.fields['is_default_shipping'].initial = True
            form.fields['is_default_billing'].initial = True

    # Ajout des classes d'erreur pour chaque champ
    is_invalid_prenom = "is-invalid" if form['prenom'].errors else ""
    is_invalid_nom = "is-invalid" if form['nom'].errors else ""
    is_invalid_rue = "is-invalid" if form['rue'].errors else ""
    is_invalid_complement = "is-invalid" if form['complement'].errors else ""
    is_invalid_code_postal = "is-invalid" if form['code_postal'].errors else ""
    is_invalid_ville = "is-invalid" if form['ville'].errors else ""
    is_invalid_pays = "is-invalid" if form['pays'].errors else ""

    return render(request, 'utilisateur/mes_adresses_form.html', {
        'form': form,
        'is_invalid_prenom': is_invalid_prenom,
        'is_invalid_nom': is_invalid_nom,
        'is_invalid_rue': is_invalid_rue,
        'is_invalid_complement': is_invalid_complement,
        'is_invalid_code_postal': is_invalid_code_postal,
        'is_invalid_ville': is_invalid_ville,
        'is_invalid_pays': is_invalid_pays,
    })








@admin_required
def liste_utilisateurs(request):
    utilisateurs = Utilisateur.objects.all()
    return render(request, 'admin/liste_utilisateurs.html', {'utilisateurs': utilisateurs})





@login_required
def mettre_a_jour_quantite(request, ligne_panier_id):
    ligne_panier = get_object_or_404(LignePanier, id=ligne_panier_id, panier__utilisateur=request.user)

    if request.method == "POST":
        nouvelle_quantite = int(request.POST.get("quantite"))
        difference = nouvelle_quantite - ligne_panier.quantite

        if difference > 0:
            # Vérifier si le stock est suffisant sans le décrémenter
            if ligne_panier.produit.stock >= difference:
                ligne_panier.quantite = nouvelle_quantite
                ligne_panier.save()
            else:
                # Vérification si AJAX pour retourner une réponse JSON
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': f"Stock insuffisant pour {ligne_panier.produit.nom}."}, status=400)
                # Sinon, affichage d'un message d'erreur classique
                messages.error(request, f"Stock insuffisant pour augmenter la quantité à {nouvelle_quantite}.")
                return redirect('afficher_panier')
        else:
            # Simplement mettre à jour la quantité sans toucher au stock
            ligne_panier.quantite = nouvelle_quantite
            ligne_panier.save()

        # Calcul des sous-totaux et du total général
        sous_total = ligne_panier.produit.prix * ligne_panier.quantite
        total = sum(
            ligne.produit.prix * ligne.quantite for ligne in LignePanier.objects.filter(panier=ligne_panier.panier)
        )

        # Retour d'une réponse JSON si AJAX
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'sous_total': sous_total,
                'total': total,
            })

        # Message classique si la requête n'est pas AJAX
        messages.success(request, "Quantité mise à jour.")
    return redirect('afficher_panier')






@login_required
def supprimer_article(request, ligne_panier_id):
    """
    Supprime un article du panier sans modifier le stock,
    car le stock est déjà géré lors de la validation ou annulation de commande.
    """
    ligne_panier = get_object_or_404(LignePanier, id=ligne_panier_id)

    if ligne_panier.produit:  # Vérifie si le produit existe
        produit = ligne_panier.produit

        # ✅ Ne pas modifier le stock ici, car il sera géré lors de la commande

    # Supprime la ligne du panier
    ligne_panier.delete()

    messages.success(request, "Article supprimé du panier.")
    return redirect('afficher_panier')







def suggestions_produits(request):
    terme = request.GET.get('q', '').strip()
    if terme:
        produits = Produit.objects.filter(nom__icontains=terme).select_related('categorie')[:10]  # Limitez les résultats
        suggestions = [
            {
                'id': p.id, 
                'nom': p.nom,
                'prix': float(p.prix),  # Convertir Decimal en float pour la sérialisation JSON
                'categorie': p.categorie.nom if p.categorie else None
            } 
            for p in produits
        ]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)




@login_required
def supprimer_adresse(request, adresse_id):
    adresse = get_object_or_404(Adresse, id=adresse_id, utilisateur=request.user)
    
    if request.method == 'POST':
        # Si l'adresse est par défaut, il faut gérer ce cas
        if adresse.is_default_shipping:
            # Chercher une autre adresse pour la définir comme adresse de livraison par défaut
            autre_adresse = Adresse.objects.filter(utilisateur=request.user, is_deleted=False).exclude(id=adresse_id).first()
            if autre_adresse:
                autre_adresse.is_default_shipping = True
                autre_adresse.save()
        
        if adresse.is_default_billing:
            # Chercher une autre adresse pour la définir comme adresse de facturation par défaut
            autre_adresse = Adresse.objects.filter(utilisateur=request.user, is_deleted=False).exclude(id=adresse_id).first()
            if autre_adresse:
                autre_adresse.is_default_billing = True
                autre_adresse.save()
        
        # Soft delete: marquer comme supprimée au lieu de réellement supprimer
        adresse.is_deleted = True
        adresse.is_default_shipping = False
        adresse.is_default_billing = False
        adresse.save()
        
        messages.success(request, "Adresse supprimée avec succès.")
    
    return redirect('mes_adresses')







def rechercher_produits(request):
    query = request.GET.get('q', '').strip()  # Récupère la requête et enlève les espaces
    produits = Produit.objects.filter(
        Q(nom__icontains=query) |  # Recherche insensible à la casse dans le nom
        Q(description__icontains=query)  # Recherche dans la description
    ).select_related('categorie').order_by('categorie__nom', 'nom') if query else []

    return render(request, 'produits/rechercher.html', {'produits': produits, 'query': query})





@login_required
def autocomplete_produits(request):
    query = request.GET.get('q', '').strip()
    if query:
        produits = Produit.objects.filter(nom__icontains=query)[:10]  # Limite à 10 résultats
        suggestions = [{'id': p.id, 'nom': p.nom} for p in produits]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)





def suggestions_produits(request):
    terme = request.GET.get('q', '').strip()
    if terme:
        produits = Produit.objects.filter(nom__icontains=terme).select_related('categorie')[:10]  # Limitez les résultats
        suggestions = [
            {
                'id': p.id, 
                'nom': p.nom,
                'prix': float(p.prix),  # Convertir Decimal en float pour la sérialisation JSON
                'categorie': p.categorie.nom if p.categorie else None
            } 
            for p in produits
        ]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)




@login_required
def mon_compte(request):
    user = request.user
    
    # Déterminer le formulaire actif (profil ou mot de passe)
    form_type = request.GET.get('form', 'profil')
    
    # Initialiser les deux formulaires
    profile_form = ModifierProfilForm(instance=user)
    password_form = ModifierMotDePasseForm(user)
    
    if request.method == 'POST':
        # Déterminer le type de formulaire soumis
        form_type = request.POST.get('form_type', 'profil')
        
        if form_type == 'profil':
            profile_form = ModifierProfilForm(request.POST, instance=user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil mis à jour avec succès ✓")
                return redirect('mon_compte')
        else:  # form_type == 'password'
            password_form = ModifierMotDePasseForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                messages.success(request, "Mot de passe mis à jour avec succès ✓")
                return redirect('mon_compte')
    
    return render(request, 'utilisateur/mon_compte.html', {
        'user': user,
        'profile_form': profile_form,
        'password_form': password_form,
        'form_type': form_type
    })




@login_required
def update_shipping_address(request, adresse_id):
    if request.method == 'POST':
        try:
            adresse = get_object_or_404(Adresse, id=adresse_id, utilisateur=request.user, is_deleted=False)
            
            # Mettre à jour l'adresse de livraison pour cette commande
            request.session['adresse_livraison_id'] = str(adresse_id)
            
            # Sécuriser toutes les valeurs pour éviter undefined
            prenom = adresse.prenom if adresse.prenom else ""
            nom = adresse.nom if adresse.nom else ""
            # Vérifier si c'est adresse ou rue
            rue = ""
            if hasattr(adresse, 'adresse'):
                rue = adresse.adresse if adresse.adresse else ""
            else:
                rue = adresse.rue if adresse.rue else ""
            complement = adresse.complement if adresse.complement else ""
            code_postal = adresse.code_postal if adresse.code_postal else ""
            ville = adresse.ville if adresse.ville else ""
            pays = adresse.pays if adresse.pays else ""
            
            print(f"DEBUG - Adresse livraison ID {adresse_id} sécurisée: rue='{rue}'")
            
            return JsonResponse({
                'success': True,
                'prenom': prenom,
                'nom': nom,
                'rue': rue,
                'complement': complement,
                'code_postal': code_postal,
                'ville': ville,
                'pays': pays
            })
        except Exception as e:
            print(f"ERREUR update_shipping_address: {str(e)}")
            return JsonResponse({
                'success': False, 
                'error': 'Erreur lors de la récupération de l\'adresse',
                'details': str(e)
            }, status=500)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)

@require_POST
def update_billing_address(request, adresse_id):
    try:
        adresse = get_object_or_404(Adresse, id=adresse_id, utilisateur=request.user, is_deleted=False)
        
        # Mettre à jour l'adresse de facturation pour cette commande
        request.session['adresse_facturation_id'] = str(adresse_id)
        
        # Sécuriser toutes les valeurs pour éviter undefined
        prenom = adresse.prenom if adresse.prenom else ""
        nom = adresse.nom if adresse.nom else ""
        # Vérifier si c'est adresse ou rue
        rue = ""
        if hasattr(adresse, 'adresse'):
            rue = adresse.adresse if adresse.adresse else ""
        else:
            rue = adresse.rue if adresse.rue else ""
        complement = adresse.complement if adresse.complement else ""
        code_postal = adresse.code_postal if adresse.code_postal else ""
        ville = adresse.ville if adresse.ville else ""
        pays = adresse.pays if adresse.pays else ""
        
        print(f"DEBUG - Adresse facturation ID {adresse_id} sécurisée: rue='{rue}'")
        
        return JsonResponse({
            'success': True,
            'prenom': prenom,
            'nom': nom,
            'rue': rue,
            'complement': complement,
            'code_postal': code_postal,
            'ville': ville,
            'pays': pays
        })
    except Exception as e:
        print(f"ERREUR update_billing_address: {str(e)}")
        return JsonResponse({
            'success': False, 
            'error': 'Erreur lors de la récupération de l\'adresse',
            'details': str(e)
        }, status=500)

@login_required
def definir_adresse_livraison(request, pk):
    adresse = get_object_or_404(Adresse, pk=pk, utilisateur=request.user, is_deleted=False)
    
    # Désactive l'adresse de livraison par défaut actuelle
    Adresse.objects.filter(utilisateur=request.user, is_default_shipping=True).update(is_default_shipping=False)
    
    # Définit la nouvelle adresse de livraison par défaut
    adresse.is_default_shipping = True
    adresse.save()
    
    messages.success(request, "Adresse de livraison par défaut mise à jour.")
    return redirect('mes_adresses')

@login_required
def definir_adresse_facturation(request, pk):
    adresse = get_object_or_404(Adresse, pk=pk, utilisateur=request.user, is_deleted=False)
    
    # Désactive l'adresse de facturation par défaut actuelle
    Adresse.objects.filter(utilisateur=request.user, is_default_billing=True).update(is_default_billing=False)
    
    # Définit la nouvelle adresse de facturation par défaut
    adresse.is_default_billing = True
    adresse.save()
    
    messages.success(request, "Adresse de facturation par défaut mise à jour.")
    return redirect('mes_adresses')

@login_required
def generer_facture_pdf(request, commande_id):
    # Récupérer la commande
    commande = get_object_or_404(Commande, id=commande_id, utilisateur=request.user)
    
    # Créer un tampon en mémoire pour le PDF
    buffer = io.BytesIO()
    
    # Créer le document PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
        title=f"Facture {commande.id}"
    )
    
    # Conteneur pour les éléments du PDF
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(
        name='InvoiceTitle', 
        parent=styles['Heading1'], 
        alignment=1,
        spaceAfter=20
    ))
    
    # Classe personnalisée pour positionner le logo en haut à gauche sans tenir compte des marges
    class LogoCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self.logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo-header1.jpg')
            
        def showPage(self):
            if os.path.exists(self.logo_path):
                self.saveState()
                img = utils.ImageReader(self.logo_path)
                # Positionner le logo dans le coin supérieur gauche
                self.drawImage(img, 20, A4[1] - 100, width=180, height=96)
                self.restoreState()
            canvas.Canvas.showPage(self)
    
    # Titre
    elements.append(Paragraph(f"FACTURE N° {commande.id}", styles['InvoiceTitle']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Date et informations
    elements.append(Paragraph(f"Date: {commande.date_commande.strftime('%d/%m/%Y')}", styles['Normal']))
    elements.append(Paragraph(f"Référence: CMD-{commande.id}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Informations client et adresses
    elements.append(Paragraph("Client:", styles['Heading3']))
    elements.append(Paragraph(f"{commande.utilisateur.prenom} {commande.utilisateur.nom}", styles['Normal']))
    elements.append(Paragraph(f"Email: {commande.utilisateur.email}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Adresse de facturation
    elements.append(Paragraph("Adresse de facturation:", styles['Heading4']))
    elements.append(Paragraph(f"{commande.adresse_facturation.prenom} {commande.adresse_facturation.nom}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.rue}", styles['Normal']))
    if commande.adresse_facturation.complement:
        elements.append(Paragraph(f"{commande.adresse_facturation.complement}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.code_postal} {commande.adresse_facturation.ville}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_facturation.pays}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))
    
    # Adresse de livraison
    elements.append(Paragraph("Adresse de livraison:", styles['Heading4']))
    elements.append(Paragraph(f"{commande.adresse_livraison.prenom} {commande.adresse_livraison.nom}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.rue}", styles['Normal']))
    if commande.adresse_livraison.complement:
        elements.append(Paragraph(f"{commande.adresse_livraison.complement}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.code_postal} {commande.adresse_livraison.ville}", styles['Normal']))
    elements.append(Paragraph(f"{commande.adresse_livraison.pays}", styles['Normal']))
    elements.append(Spacer(1, 1*cm))
    
    # Détails des produits
    # En-têtes
    data = [["Produit", "Quantité", "Prix unitaire HT", "Total HT"]]
    
    # Calcul des totaux
    total_ttc = commande.get_total()
    coeff_tva = Decimal("1.21")
    total_ht = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)
    livraison_prix = commande.prix_livraison
    
    # Récupérer les détails des produits
    for ligne in commande.lignes_commande.all():
        produit = ligne.produit
        quantite = ligne.quantite
        prix_ttc = ligne.prix_unitaire
        prix_ht = prix_ttc / coeff_tva
        sous_total_ht = prix_ht * quantite
        
        data.append([
            produit.nom,
            str(quantite),
            f"{prix_ht:.2f} €",
            f"{sous_total_ht:.2f} €"
        ])
    
    # Créer la table
    table = Table(data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (3, -1), 'RIGHT'),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*cm))
    
    # Totaux
    data_totaux = [
        ["Sous-total HT", f"{total_ht:.2f} €"],
        ["TVA (21%)", f"{total_tva:.2f} €"],
        ["Total TTC", f"{total_ttc:.2f} €"],
        ["Livraison", f"{livraison_prix:.2f} €" if livraison_prix > 0 else "Gratuite"],
        ["Total TTC avec livraison", f"{total_ttc + livraison_prix:.2f} €"],
    ]
    
    table_totaux = Table(data_totaux, colWidths=[12*cm, 4*cm])
    table_totaux.setStyle(TableStyle([
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table_totaux)
    
    # Notes
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Merci pour votre achat chez YemTech Pro !", styles['Center']))
    elements.append(Paragraph("Cette facture a été générée automatiquement.", styles['Center']))
    
    # Construire le PDF avec le canvas personnalisé
    doc.build(elements, canvasmaker=LogoCanvas)
    
    # Positionner le curseur au début du buffer
    buffer.seek(0)
    
    # Retourner le PDF comme une réponse à télécharger
    return FileResponse(buffer, as_attachment=True, filename=f"facture_{commande.id}.pdf")




@login_required
def vider_panier(request):
    """
    Supprime tous les articles du panier de l'utilisateur.
    """
    utilisateur = request.user
    panier = get_object_or_404(Panier, utilisateur=utilisateur)
    
    # Supprimer toutes les lignes du panier
    LignePanier.objects.filter(panier=panier).delete()
    
    messages.success(request, "Votre panier a été vidé avec succès.")
    return redirect('afficher_panier')




@require_POST
def api_ajouter_adresse(request):
    """
    Vue API pour ajouter une adresse sans redirection.
    Renvoie l'adresse créée au format JSON pour mise à jour côté client.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentification requise'}, status=401)

    user = request.user
    adresse = Adresse(utilisateur=user)
    
    # Récupérer les données du formulaire
    prenom = request.POST.get('prenom', '')
    nom = request.POST.get('nom', '')
    rue = request.POST.get('rue', '')
    complement = request.POST.get('complement', '')
    code_postal = request.POST.get('code_postal', '')
    ville = request.POST.get('ville', '')
    pays = request.POST.get('pays', 'Belgique')
    is_default_shipping = request.POST.get('is_default_shipping') == 'on'
    is_default_billing = request.POST.get('is_default_billing') == 'on'
    
    # Validation minimale
    if not prenom or not nom or not rue or not code_postal or not ville:
        return JsonResponse({
            'success': False, 
            'message': 'Veuillez remplir tous les champs obligatoires'
        }, status=400)
    
    # Mettre à jour l'adresse
    adresse.prenom = prenom
    adresse.nom = nom
    adresse.rue = rue
    adresse.complement = complement
    adresse.code_postal = code_postal
    adresse.ville = ville
    adresse.pays = pays
    adresse.is_default_shipping = is_default_shipping
    adresse.is_default_billing = is_default_billing
    
    # Gérer les adresses par défaut
    if is_default_shipping:
        Adresse.objects.filter(utilisateur=user, is_default_shipping=True, is_deleted=False).update(is_default_shipping=False)
    
    if is_default_billing:
        Adresse.objects.filter(utilisateur=user, is_default_billing=True, is_deleted=False).update(is_default_billing=False)
    
    adresse.save()
    
    # Renvoyer les données de l'adresse créée
    return JsonResponse({
        'success': True,
        'message': 'Adresse ajoutée avec succès',
        'adresse': {
            'id': adresse.id,
            'prenom': adresse.prenom,
            'nom': adresse.nom,
            'rue': adresse.rue,
            'complement': adresse.complement,
            'code_postal': adresse.code_postal,
            'ville': adresse.ville,
            'pays': adresse.pays,
            'is_default_shipping': adresse.is_default_shipping,
            'is_default_billing': adresse.is_default_billing
        }
    })

@require_POST
def update_toggle_addresses(request):
    """Met à jour l'état du toggle pour utiliser la même adresse pour la livraison et la facturation."""
    is_same = request.POST.get('is_same', 'false').lower() == 'true'
    request.session['toggle_facturation_identique'] = is_same
    
    # Ne synchroniser l'adresse de facturation avec celle de livraison que lorsque
    # le toggle est activé ET que l'utilisateur n'a pas encore choisi une adresse différente
    if is_same and 'adresse_livraison_id' in request.session:
        # Synchroniser l'adresse de facturation avec celle de livraison
        request.session['adresse_facturation_id'] = request.session['adresse_livraison_id']
    
    return JsonResponse({'success': True})



