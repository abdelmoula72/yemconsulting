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
from django.views.decorators.http import require_http_methods
from .models import Produit, Categorie, Panier, LignePanier, Utilisateur, Commande
from .forms import InscriptionForm, ModifierProfilForm
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
from .forms import ModifierProfilForm
from django.templatetags.static import static






__all__ = ["next_business_day", "business_days_after"]

def next_business_day(base=None):
    """Renvoie le prochain jour ouvrable (lundi-vendredi)."""
    base = base or timezone.localdate()
    d = base
    while d.weekday() >= 5:          # 5 = samedi, 6 = dimanche
        d += dt.timedelta(days=1)
    return d

def business_days_after(n, base=None):
    """Ajoute *n* jours ouvrables à *base* (par défaut aujourd’hui)."""
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

    # ────────── options de livraison dynamiques ──────────
    LIVRAISON_OPTIONS = {
        "standard": {
            "libelle": "Livraison standard",
            "prix":    Decimal("0.00"),
            "debut":   STANDARD_DEBUT,   # objets date
            "fin":     STANDARD_FIN,
        },
        "express": {
            "libelle": "Livraison Express",
            "prix":    Decimal("7.00"),
            "debut":   DEMAIN,
            "fin":     None,             # pas de fin pour l’express
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

    # ────────── GET : prépare l’affichage ──────────
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
         "form"            : form,
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
    commande = Commande.objects.create(
        utilisateur=utilisateur,
        panier=panier,
        statut="confirmee",
    )

    commande.quantites_initiales = {
    str(l.produit.id): l.quantite
    for l in lignes_panier
    }
    
    commande.save(update_fields=["quantites_initiales"])

    # ────────── totaux (HT / TVA / TTC) ──────────
    total_ttc = sum(l.produit.prix * l.quantite for l in lignes_panier)

    # ► prix de livraison éventuellement stocké en session (page confirmation-panier)
    livraison_prix = Decimal(request.session.pop("livraison_prix", "0.00"))
    total_ttc += livraison_prix

    coeff_tva = Decimal("1.21")
    total_ht  = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # ────────── préparation des lignes pour l’e-mail ──────────
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
    total = 0

    for produit_id, quantite in commande.quantites_initiales.items():
        produit = get_object_or_404(Produit, id=produit_id)
        sous_total = produit.prix * quantite

        # calcul de l’URL de la miniature
        if produit.image and produit.image.url:
            img_url = produit.image.url
        else:
            img_url = static('default.jpg')

        lignes_commande.append({
            'produit': produit,
            'quantite': quantite,
            'prix': produit.prix,
            'sous_total': sous_total,
            'image_url': img_url,
        })
        total += sous_total

    return render(request, 'commande/confirmation_commande.html', {
        'commande': commande,
        'lignes_commande': lignes_commande,
        'total': total,
    })









@login_required
def historique_commandes(request):
    utilisateur = request.user  # Utilise l'utilisateur authentifié directement
    commandes = Commande.objects.filter(utilisateur=utilisateur).order_by('-date_commande')

    if not commandes.exists():
        messages.info(request, "Aucune commande trouvée.")
        return render(request, 'commande/historique_commandes.html', {'commandes': []})

    return render(request, 'commande/historique_commandes.html', {'commandes': commandes})





@login_required
def annuler_commande(request, commande_id):
    commande = get_object_or_404(Commande, id=commande_id, utilisateur=request.user)

    if commande.statut != 'en_attente':
        messages.error(request, "Cette commande ne peut plus être annulée.")
        return redirect('historique_commandes')

    # Restaurer le stock en utilisant les quantités initiales enregistrées
    with transaction.atomic():  
        for produit_id, quantite in commande.quantites_initiales.items():
            produit = Produit.objects.select_for_update().get(id=produit_id)
            produit.stock += quantite
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
    return render(request, 'registration/inscription.html', {'form': form})




@login_required
def modifier_profil(request):
    utilisateur = request.user

    # On récupère next dans GET ou POST, sinon on tombe sur l'accueil
    next_page = (
        request.POST.get("next")
        or request.GET.get("next")
        or reverse("liste_categories")
    )

    if request.method == "POST":
        form = ModifierProfilForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour ✔")
            return redirect(next_page)       # ← redirection immédiate
    else:
        form = ModifierProfilForm(instance=utilisateur)

    return render(request, "utilisateur/modifier_profil.html", {
        "form": form,
        "next": next_page,
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



