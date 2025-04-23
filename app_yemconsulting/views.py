from django.shortcuts import render, get_object_or_404, redirect
from .models import Produit, Categorie, Panier, LignePanier, Utilisateur, Commande
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import InscriptionForm, ModifierProfilForm
from django.contrib.auth import login
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.db import transaction
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import format_html
import stripe
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from decimal import Decimal, ROUND_HALF_UP
from django.template.loader import render_to_string         #  ← import ajouté
from django.utils.html import format_html, strip_tags
from django.urls import reverse
from email.utils import make_msgid
from mimetypes import guess_type
from django.contrib.staticfiles.storage import staticfiles_storage
from email.mime.image import MIMEImage
from django.contrib.staticfiles.storage import staticfiles_storage
import os 
from datetime import date, timedelta
from django.utils.formats import date_format
import locale



stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def stripe_checkout(request):
    utilisateur = request.user
    panier = get_object_or_404(Panier, utilisateur=utilisateur)
    lignes = LignePanier.objects.filter(panier=panier)

    if not lignes.exists():
        messages.error(request, "Votre panier est vide.")
        return redirect('afficher_panier')

    line_items = []
    for ligne in lignes:
        produit = ligne.produit
        line_items.append({
            'price_data': {
                'currency': 'eur',
                'product_data': {
                    'name': produit.nom,
                },
                'unit_amount': int(produit.prix * 100),  # en centimes
            },
            'quantity': ligne.quantite,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri(reverse('stripe_success')),
        cancel_url=request.build_absolute_uri(reverse('afficher_panier')),
    )

    return redirect(session.url)


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
    panier = get_object_or_404(Panier, utilisateur=utilisateur)
    lignes_panier = LignePanier.objects.filter(panier=panier)
    
    # Calcul du total général et des sous-totaux pour chaque ligne
    lignes_commande = []
    total = 0
    for ligne in lignes_panier:
        sous_total = ligne.produit.prix * ligne.quantite
        lignes_commande.append({
            'ligne': ligne,
            'sous_total': sous_total
        })
        total += sous_total

    return render(request, 'panier/afficher_panier.html', {
        'lignes_commande': lignes_commande,
        'total': total,
        'panier': panier
    })












@login_required
def passer_commande(request):
    utilisateur = get_object_or_404(Utilisateur, email=request.user.email)
    panier      = get_object_or_404(Panier, utilisateur=utilisateur)
    methode_paiement = request.session.pop('methode_paiement', 'Inconnu')

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
            prod.save()
            if prod.stock <= 15:
                produits_alerte_stock.add(prod)

    # ────────── création de la commande ──────────
    commande = Commande.objects.create(
        utilisateur=utilisateur,
        panier=panier,
        statut='confirmee',
    )

    # ────────── totaux HT / TVA / TTC ──────────
    total_ttc = sum(l.produit.prix * l.quantite for l in lignes_panier)
    coeff_tva = Decimal("1.21")
    total_ht  = (total_ttc / coeff_tva).quantize(Decimal("0.01"), ROUND_HALF_UP)
    total_tva = (total_ttc - total_ht).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # ────────── préparation des lignes pour l’e-mail ──────────
    email_lignes        = []
    images_a_attacher   = []      # liste de tuples (cid, chemin_fichier)

    for ligne in lignes_panier:
        prod = ligne.produit

        # chemin physique de l’image (MEDIA ou fallback STATIC)
        if prod.image and prod.image.name:
            img_path = prod.image.path
        else:
            img_path = staticfiles_storage.path('default.jpg')

        # CID unique pour insertion inline
        cid       = make_msgid(domain='yemconsulting.local')       # ex. '<abc@yem…>'
        cid_clean = cid[1:-1]                                      # on retire < >

        email_lignes.append({
            "nom"      : prod.nom,
            "quantite" : ligne.quantite,
            "prix"     : prod.prix,
            "img_cid"  : cid_clean,           # utilisé dans le template
        })
        images_a_attacher.append((cid, img_path))

    # contexte pour les templates

        try:
            locale.setlocale(locale.LC_TIME, "fr_FR.UTF-8")  # Linux / macOS
        except locale.Error:
            try:
                locale.setlocale(locale.LC_TIME, "French_France")  # Windows
            except locale.Error:
                pass  # on garde la locale système si introuvable

    def format_livraison(offset):
        """
        Retourne une date française lisible, sans zéro initial sur le jour,
        compatible Windows ET Linux.
        """
        d       = date.today() + timedelta(days=offset)
        weekday = d.strftime("%a")          # mer.
        month   = d.strftime("%b")          # avr.
        return f"{weekday}, {d.day} {month} {d.year}"

    livraison_debut = format_livraison(2)   # mer., 2 avr. 2025
    livraison_fin   = format_livraison(3)   # jeu., 3 avr. 2025
    

    ctx = {
        "utilisateur"     : utilisateur,
        "commande"        : commande,
        "lignes"          : email_lignes,
        "total_ht"        : total_ht,
        "total_tva"       : total_tva,
        "total_ttc"       : total_ttc,
        "methode_paiement": methode_paiement,
        "url_commande"    : request.build_absolute_uri( reverse("confirmation_commande", args=[commande.id])),
        "livraison_debut": livraison_debut,
        "livraison_fin"  : livraison_fin,
    }

    html_body = render_to_string("emails/confirmation_commande.html", ctx)
    text_body = render_to_string("emails/confirmation_commande.txt", ctx)

    # ---------- création du message ----------
    mail = EmailMultiAlternatives(
        subject="Confirmation de votre commande",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[utilisateur.email],
    )
    mail.attach_alternative(html_body, "text/html")

    # jointure des miniatures (inline)
    for cid, path in images_a_attacher:
        try:
            with open(path, "rb") as fp:
                subtype = guess_type(path)[0].split("/")[1]   # 'jpeg', 'png'…
                img = MIMEImage(fp.read(), _subtype=subtype)
                img.add_header("Content-ID", cid)
                img.add_header("Content-Disposition", "inline",
                            filename=os.path.basename(path))
                mail.attach(img)
        except FileNotFoundError:
            pass  # on ignore simplement

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
            f"<strong>Attention !</strong><br>{corps_html}", "text/html"
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
        lignes_commande.append({
            'produit': produit,
            'quantite': quantite,
            'prix': produit.prix,
            'sous_total': sous_total,
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
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('modifier_profil')
    else:
        form = ModifierProfilForm(instance=utilisateur)
    return render(request, 'utilisateur/modifier_profil.html', {'form': form})


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



