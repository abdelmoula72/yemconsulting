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
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html, strip_tags
from django.utils.formats import date_format
from django.views.decorators.http import require_http_methods, require_POST
from .models import Produit, Categorie, Panier, LignePanier, Utilisateur, Commande, Adresse
from .forms import (InscriptionForm, ModifierProfilForm, DonneesPersonnellesForm, AdresseForm)
import stripe
from email.mime.image import MIMEImage
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage          # pour les miniatures inline
import datetime as dt
from django.utils import timezone
from app_yemconsulting.utils.date_helpers import business_days_after
import mimetypes
from .models import Panier, LignePanier, Commande
from django.templatetags.static import static
from django.contrib.auth.forms import PasswordChangeForm








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

    # Récupérer les adresses existantes de la session ou utiliser les adresses par défaut
    adresse_livraison_id = request.session.get('adresse_livraison_id')
    adresse_facturation_id = request.session.get('adresse_facturation_id')
    
    if adresse_livraison_id:
        # Utiliser l'adresse de livraison de la session
        adresse_livraison = get_object_or_404(Adresse, id=adresse_livraison_id, utilisateur=utilisateur, active=True)
    else:
        # Charger l'adresse de livraison par défaut pour l'affichage initial seulement
        adresse_livraison = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, active=True).first()
        # Mettre à jour la session uniquement si aucune adresse n'est déjà sélectionnée
        if adresse_livraison:
            request.session['adresse_livraison_id'] = adresse_livraison.id
    
    if adresse_facturation_id:
        # Utiliser l'adresse de facturation de la session
        adresse_facturation = get_object_or_404(Adresse, id=adresse_facturation_id, utilisateur=utilisateur, active=True)
    else:
        # Charger l'adresse de facturation par défaut pour l'affichage initial seulement
        adresse_facturation = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, active=True).first()
        # Mettre à jour la session uniquement si aucune adresse n'est déjà sélectionnée
        if adresse_facturation:
            request.session['adresse_facturation_id'] = adresse_facturation.id

    # Récupérer toutes les adresses actives de l'utilisateur
    adresses = Adresse.objects.filter(utilisateur=utilisateur, active=True)

    # Déterminer si les deux adresses sont identiques (même id)
    toggle_facturation_identique = adresse_livraison and adresse_facturation and adresse_livraison.id == adresse_facturation.id

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
        choix = request.POST.get("livraison", "standard")
        if choix not in LIVRAISON_OPTIONS:
            choix = "standard"

        # on mémorise le choix pour la session
        request.session["livraison_select"] = choix
        request.session["livraison_prix"]   = str(LIVRAISON_OPTIONS[choix]["prix"])

        return redirect("stripe_checkout")   # (ou la route de paiement voulue)

    # ────────── GET : prépare l'affichage ──────────
    livraison_select = request.session.get("livraison_select", "standard")
    livraison_info   = LIVRAISON_OPTIONS[livraison_select]

    lignes      = []
    sous_total  = Decimal("0.00")

    for lp in lignes_qs:
        prod = lp.produit
        img_url = prod.image.url if prod.image else static("default.jpg")
        lignes.append({
            "image_url": img_url,
            "nom"      : prod.nom,
            "quantite" : lp.quantite,
            "prix"     : prod.prix,
        })
        sous_total += prod.prix * lp.quantite

    total_ttc = sous_total + livraison_info["prix"]

    form = ModifierProfilForm(instance=request.user)

    context = {
        "utilisateur"      : utilisateur,
        "lignes"           : lignes,
        "sous_total"       : sous_total,
        "total_ttc"        : total_ttc,
        "livraisons"       : LIVRAISON_OPTIONS,
        "livraison_select" : livraison_select,
        "livraison"        : livraison_info,
        "form"             : form,
        "adresse_livraison": adresse_livraison,
        "adresse_facturation": adresse_facturation,
        "adresses"         : adresses,
        "toggle_facturation_identique": toggle_facturation_identique,
    }
    return render(request, "panier/confirmation_panier.html", context)








stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def stripe_checkout(request):
    utilisateur = request.user
    panier      = get_object_or_404(Panier, utilisateur=utilisateur)
    lignes      = LignePanier.objects.filter(panier=panier)

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
                "currency"    : "eur",
                "product_data": {"name": p.nom},
                "unit_amount" : int(p.prix * 100),   # centimes
            },
            "quantity": ligne.quantite,
        })

    # 🟪 frais de livraison éventuels
    livraison_prix = Decimal(request.session.get("livraison_prix", "0.00"))
    if livraison_prix > 0:
        line_items.append({
            "price_data": {
                "currency"    : "eur",
                "product_data": {"name": "Frais de livraison"},
                "unit_amount" : int(livraison_prix * 100),
            },
            "quantity": 1,
        })

    # création de la Session Stripe
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=line_items,
        mode="payment",
        success_url=request.build_absolute_uri(reverse("stripe_success")),
        cancel_url=request.build_absolute_uri(reverse("afficher_panier")),
    )

    return redirect(session.url, code=303)



@login_required
def stripe_success(request):
    # 💳 Indiquer que le paiement a été effectué via Stripe
    request.session['methode_paiement'] = 'Stripe'
    
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

    

    if produit.stock < quantite:
        return JsonResponse({'success': False, 'message': f"Stock insuffisant ({produit.stock} restants)."}, status=400)

    utilisateur = request.user
    panier, created = Panier.objects.get_or_create(utilisateur=utilisateur)
    ligne_panier, created = LignePanier.objects.get_or_create(panier=panier, produit=produit)

    # ✅ Vérifie si la quantité est bien mise à jour
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
    panier      = get_object_or_404(Panier, utilisateur=utilisateur)

    lignes_commande = []
    total = Decimal("0.00")

    for ligne in (
        LignePanier.objects
        .select_related("produit")
        .filter(panier=panier)
    ):
        prod = ligne.produit

        img_url = prod.image.url if prod.image else static("default.jpg")

        lignes_commande.append({
            "id"        : ligne.id,            # ← OBLIGATOIRE !
            "nom"       : prod.nom,
            "prix"      : prod.prix,
            "quantite"  : ligne.quantite,
            "sous_total": prod.prix * ligne.quantite,
            "img_url"   : img_url,
        })

        total += prod.prix * ligne.quantite

    return render(
        request,
        "panier/afficher_panier.html",
        {"lignes_commande": lignes_commande, "total": total}
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
            adresse_livraison = Adresse.objects.get(id=adresse_livraison_id, utilisateur=utilisateur, active=True)
            print(f"Utilisation de l'adresse de livraison sélectionnée: {adresse_livraison.id} - {adresse_livraison}")
        except Adresse.DoesNotExist:
            print(f"L'adresse de livraison ID {adresse_livraison_id} n'existe pas ou n'est pas active")
            # Fallback à l'adresse par défaut
            adresse_livraison = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, active=True).first()
            if adresse_livraison:
                adresse_livraison_id = adresse_livraison.id
                request.session['adresse_livraison_id'] = adresse_livraison_id
                print(f"Fallback à l'adresse de livraison par défaut: {adresse_livraison.id}")
            else:
                print("Aucune adresse de livraison trouvée")
                return JsonResponse(
                    {"success": False, "message": "Aucune adresse de livraison valide trouvée."},
                    status=400
                )
    else:
        # Aucune adresse en session, utiliser l'adresse par défaut
        adresse_livraison = Adresse.objects.filter(utilisateur=utilisateur, is_default_shipping=True, active=True).first()
        if adresse_livraison:
            adresse_livraison_id = adresse_livraison.id
            request.session['adresse_livraison_id'] = adresse_livraison_id
            print(f"Utilisation de l'adresse de livraison par défaut: {adresse_livraison.id}")
        else:
            print("Aucune adresse de livraison par défaut trouvée")
            return JsonResponse(
                {"success": False, "message": "Aucune adresse de livraison sélectionnée."},
                status=400
            )

    # Récupérer l'adresse de facturation de la session
    adresse_facturation_id = request.session.get('adresse_facturation_id')
    print(f"Adresse de facturation ID dans session: {adresse_facturation_id}")
    
    # Si l'ID existe dans la session, récupérer cette adresse spécifique
    if adresse_facturation_id:
        try:
            adresse_facturation = Adresse.objects.get(id=adresse_facturation_id, utilisateur=utilisateur, active=True)
            print(f"Utilisation de l'adresse de facturation sélectionnée: {adresse_facturation.id} - {adresse_facturation}")
        except Adresse.DoesNotExist:
            print(f"L'adresse de facturation ID {adresse_facturation_id} n'existe pas ou n'est pas active")
            # Fallback à l'adresse par défaut ou à l'adresse de livraison
            adresse_facturation = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, active=True).first()
            if adresse_facturation:
                print(f"Fallback à l'adresse de facturation par défaut: {adresse_facturation.id}")
            else:
                print(f"Utilisation de l'adresse de livraison comme adresse de facturation: {adresse_livraison.id}")
                adresse_facturation = adresse_livraison
    else:
        # Aucune adresse en session, utiliser l'adresse par défaut ou l'adresse de livraison
        adresse_facturation = Adresse.objects.filter(utilisateur=utilisateur, is_default_billing=True, active=True).first()
        if adresse_facturation:
            print(f"Utilisation de l'adresse de facturation par défaut: {adresse_facturation.id}")
        else:
            print(f"Aucune adresse de facturation par défaut, utilisation de l'adresse de livraison: {adresse_livraison.id}")
            adresse_facturation = adresse_livraison

    # ────────── gestion du stock ──────────
    produits_alerte_stock = set()
    for ligne in lignes_panier:
        prod = ligne.produit
        if prod.stock >= ligne.quantite:
            prod.stock -= ligne.quantite
            prod.save(update_fields=["stock"])
            if prod.stock <= 15:
                produits_alerte_stock.add(prod)

    # ────────── création de la commande ──────────
    livraison_prix = Decimal(request.session.pop("livraison_prix", "0.00"))
    
    # Préparer les adresses au format JSON
    adresse_livraison_json = {
        'prenom': adresse_livraison.prenom,
        'nom': adresse_livraison.nom,
        'adresse': adresse_livraison.adresse,
        'complement': adresse_livraison.complement,
        'code_postal': adresse_livraison.code_postal,
        'ville': adresse_livraison.ville,
        'pays': adresse_livraison.pays
    }
    
    adresse_facturation_json = {
        'prenom': adresse_facturation.prenom,
        'nom': adresse_facturation.nom,
        'adresse': adresse_facturation.adresse,
        'complement': adresse_facturation.complement,
        'code_postal': adresse_facturation.code_postal,
        'ville': adresse_facturation.ville,
        'pays': adresse_facturation.pays
    }
    
    commande = Commande.objects.create(
        utilisateur=utilisateur,
        panier=panier,
        statut="confirmee",
        adresse_livraison=adresse_livraison_json,
        adresse_facturation=adresse_facturation_json,
        livraison=livraison_prix
    )

    commande.set_quantites_initiales(lignes_panier)

    # ────────── totaux (HT / TVA / TTC) ──────────
    total_ttc = Decimal(str(commande.get_total_initial()))

    # ► prix de livraison éventuellement stocké en session (page confirmation-panier)
    livraison_prix = Decimal(request.session.pop("livraison_prix", "0.00"))
    total_ttc += livraison_prix

    coeff_tva = Decimal("1.21")
    total_ht  = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # ────────── préparation des lignes pour l'e-mail ──────────
    email_lignes      = []
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
        "total_ttc"       : total_ttc,
        "methode_paiement": methode_paiement,
        "url_commande"    : request.build_absolute_uri( reverse("confirmation_commande", args=[commande.id]) ),
        "livraison_debut": livraison_debut.strftime("%a %d %b %Y"),
        "livraison_fin"  : livraison_fin.strftime("%a %d %b %Y"),
        "livraison_express": f"{express.strftime('%a')}, {express.day} {express.strftime('%b %Y')}",
        "livraison_prix"  : livraison_prix,
        "adresse_livraison": adresse_livraison_json,
    }

    html_body = render_to_string("emails/confirmation_commande.html", ctx)
    text_body = render_to_string("emails/confirmation_commande.txt", ctx)

    # ────────── mail + miniatures inline ──────────
    mail = EmailMultiAlternatives(
        subject="Confirmation de votre commande",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[utilisateur.email],
    )
    mail.attach_alternative(html_body, "text/html")

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

    # Utiliser les données de `quantites_initiales` pour les lignes de commande
    lignes_commande = []
    total = Decimal('0.00')

    for produit_id, data in commande.get_quantites_initiales().items():
        produit = get_object_or_404(Produit, id=produit_id)
        sous_total = Decimal(str(data["price"])) * Decimal(str(data["quantity"]))

        # calcul de l'URL de la miniature
        if produit.image and produit.image.url:
            img_url = produit.image.url
        else:
            img_url = static('default.jpg')

        lignes_commande.append({
            'produit': produit,
            'quantite': data["quantity"],
            'prix': data["price"],
            'sous_total': sous_total,
            'image_url': img_url,
        })
        total += sous_total

    # Ajouter le prix de livraison au total
    total_avec_livraison = total + commande.livraison

    return render(request, 'commande/confirmation_commande.html', {
        'commande': commande,
        'lignes_commande': lignes_commande,
        'total': total,
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

    # Restaurer le stock en utilisant les quantités initiales enregistrées
    with transaction.atomic():  
        for produit_id, data in commande.get_quantites_initiales().items():
            produit = Produit.objects.select_for_update().get(id=produit_id)
            produit.stock += data["quantity"]
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

    # Si aucune adresse active n'existe, rediriger vers ajout avec les deux cases pré-cochées
    if user.adresses.filter(active=True).count() == 0 and not edit_type:
        return editer_adresse(request, first_address=True)

    # Si on vient de la confirmation panier et pas de paramètre edit, rediriger vers l'adresse de livraison par défaut
    if next_url and not edit_type:
        adresse_livraison = user.adresses.filter(is_default_shipping=True, active=True).first()
        if adresse_livraison:
            url = f"{request.path}?edit=shipping&pk={adresse_livraison.pk}"
            if next_url:
                url += f"&next={next_url}"
            return redirect(url)

    if edit_type in ['shipping', 'billing']:
        return editer_adresse(request, pk=pk)

    # Récupère toutes les adresses actives
    adresses = user.adresses.filter(active=True)
    return render(request, 'utilisateur/mes_adresses_list.html', {
        'adresses': adresses,
    })

@login_required
def editer_adresse(request, pk=None, first_address=False):
    user = request.user

    # Choix de l'instance (modification vs création)
    if pk:
        adresse = get_object_or_404(Adresse, pk=pk, utilisateur=user)
    else:
        adresse = Adresse(utilisateur=user)

    if request.method == 'POST':
        form = AdresseForm(request.POST, instance=adresse)
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
        form = AdresseForm(instance=adresse)
        if first_address:
            form.fields['is_default_shipping'].initial = True
            form.fields['is_default_billing'].initial = True

    # Ajout des classes d'erreur pour chaque champ
    is_invalid_prenom = "is-invalid" if form['prenom'].errors else ""
    is_invalid_nom = "is-invalid" if form['nom'].errors else ""
    is_invalid_adresse = "is-invalid" if form['adresse'].errors else ""
    is_invalid_complement = "is-invalid" if form['complement'].errors else ""
    is_invalid_code_postal = "is-invalid" if form['code_postal'].errors else ""
    is_invalid_ville = "is-invalid" if form['ville'].errors else ""
    is_invalid_pays = "is-invalid" if form['pays'].errors else ""

    return render(request, 'utilisateur/mes_adresses_form.html', {
        'form': form,
        'adresse': adresse,
        'is_invalid_prenom': is_invalid_prenom,
        'is_invalid_nom': is_invalid_nom,
        'is_invalid_adresse': is_invalid_adresse,
        'is_invalid_complement': is_invalid_complement,
        'is_invalid_code_postal': is_invalid_code_postal,
        'is_invalid_ville': is_invalid_ville,
        'is_invalid_pays': is_invalid_pays,
    })








@staff_member_required
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
            if ligne_panier.produit.stock >= difference:
                ligne_panier.produit.stock -= difference
                ligne_panier.produit.save()
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
            # Réincrémentation du stock si la quantité est réduite
            ligne_panier.produit.stock += abs(difference)
            ligne_panier.produit.save()
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






@login_required
def rechercher_produits(request):
    query = request.GET.get('q', '').strip()  # Récupère la requête et enlève les espaces
    produits = Produit.objects.filter(
        Q(nom__icontains=query)  # Recherche insensible à la casse
    ) if query else []

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
        produits = Produit.objects.filter(nom__icontains=terme)[:10]  # Limitez les résultats
        suggestions = [{'id': p.id, 'nom': p.nom} for p in produits]
        return JsonResponse(suggestions, safe=False)
    return JsonResponse([], safe=False)




@login_required
def supprimer_adresse(request, adresse_id):
    adresse = get_object_or_404(Adresse, id=adresse_id, utilisateur=request.user)
    if request.method == 'POST':
        adresse.delete()
        messages.success(request, "Adresse supprimée avec succès.")
    return redirect('mes_adresses')




@login_required
def mon_compte(request):
    user = request.user
    if request.method == 'POST':
        pwd_form = PasswordChangeForm(user, request.POST)
        if pwd_form.is_valid():
            pwd_form.save()
            messages.success(request, "Mot de passe mis à jour ✔")
            return redirect('mon_compte')
    else:
        pwd_form = PasswordChangeForm(user)
    return render(request, 'utilisateur/mon_compte.html', {
        'user': user,
        'pwd_form': pwd_form,
    })




@login_required
def update_shipping_address(request, adresse_id):
    if request.method == 'POST':
        try:
            adresse = Adresse.objects.get(id=adresse_id, utilisateur=request.user, active=True)
            
            # Mettre à jour l'adresse de livraison pour cette commande
            request.session['adresse_livraison_id'] = adresse_id
            
            return JsonResponse({
                'success': True,
                'prenom': adresse.prenom,
                'nom': adresse.nom,
                'adresse': adresse.adresse,
                'complement': adresse.complement,
                'code_postal': adresse.code_postal,
                'ville': adresse.ville,
                'pays': adresse.pays
            })
        except Adresse.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Adresse non trouvée ou inactive'}, status=404)
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)




@login_required
def definir_adresse_livraison(request, pk):
    adresse = get_object_or_404(Adresse, pk=pk, utilisateur=request.user)
    
    # Désactive l'adresse de livraison par défaut actuelle
    Adresse.objects.filter(utilisateur=request.user, is_default_shipping=True).update(is_default_shipping=False)
    
    # Définit la nouvelle adresse de livraison par défaut
    adresse.is_default_shipping = True
    adresse.save()
    
    messages.success(request, "Adresse de livraison par défaut mise à jour.")
    return redirect('mes_adresses')

@login_required
def definir_adresse_facturation(request, pk):
    adresse = get_object_or_404(Adresse, pk=pk, utilisateur=request.user)
    
    # Désactive l'adresse de facturation par défaut actuelle
    Adresse.objects.filter(utilisateur=request.user, is_default_billing=True).update(is_default_billing=False)
    
    # Définit la nouvelle adresse de facturation par défaut
    adresse.is_default_billing = True
    adresse.save()
    
    messages.success(request, "Adresse de facturation par défaut mise à jour.")
    return redirect('mes_adresses')

@require_POST
def update_billing_address(request, adresse_id):
    adresse = get_object_or_404(Adresse, pk=adresse_id, utilisateur=request.user, active=True)
    # Stocke l'id dans la session pour la commande
    request.session['adresse_facturation_id'] = adresse_id
    return JsonResponse({
        'success': True,
        'prenom': adresse.prenom,
        'nom': adresse.nom,
        'adresse': adresse.adresse,
        'complement': adresse.complement,
        'code_postal': adresse.code_postal,
        'ville': adresse.ville,
        'pays': adresse.pays
    })



