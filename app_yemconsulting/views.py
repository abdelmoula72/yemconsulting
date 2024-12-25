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


def liste_produits(request):
    produits = Produit.objects.all()
    categories = Categorie.objects.all()
    return render(request, 'produits/liste.html', {'produits': produits, 'categories': categories})


def produits_par_categorie(request, categorie_id):
    categorie = get_object_or_404(Categorie, id=categorie_id)
    produits = Produit.objects.filter(categorie=categorie)
    categories = Categorie.objects.all()
    return render(request, 'produits/liste.html', {
        'produits': produits,
        'categories': categories,
        'categorie_active': categorie,
    })





@login_required
def ajouter_au_panier(request, produit_id):
    produit = get_object_or_404(Produit, id=produit_id)
    quantite = int(request.POST.get('quantite', 1))

    if produit.stock < quantite:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': f"Stock insuffisant pour {produit.nom}. Quantité disponible : {produit.stock}."}, status=400)
        messages.error(request, f"Stock insuffisant pour {produit.nom}. Quantité disponible : {produit.stock}.")
        return redirect('liste_produits')

    utilisateur = request.user
    panier, created = Panier.objects.get_or_create(utilisateur=utilisateur)
    ligne_panier, created = LignePanier.objects.get_or_create(panier=panier, produit=produit)
    ligne_panier.quantite = ligne_panier.quantite + quantite if not created else quantite
    ligne_panier.save()

    produit.stock -= quantite
    produit.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': f"{quantite} {produit.nom} ajouté(s) au panier."})

    messages.success(request, f"{quantite} {produit.nom} ajouté(s) au panier.")
    return redirect('afficher_panier')











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
    panier = get_object_or_404(Panier, utilisateur=utilisateur)

    if not LignePanier.objects.filter(panier=panier).exists():
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': "Votre panier est vide."}, status=400)
        messages.error(request, "Votre panier est vide.")
        return redirect('afficher_panier')

    lignes_panier = LignePanier.objects.filter(panier=panier)
    quantites_initiales = {ligne.produit.id: ligne.quantite for ligne in lignes_panier}

    # Création de la commande
    commande = Commande.objects.create(
        utilisateur=utilisateur,
        panier=panier,
        statut='en_attente',
        quantites_initiales=quantites_initiales
    )

    # Vider le panier après la commande
    lignes_panier.delete()

    # Si la requête est AJAX, retourne une réponse JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': "Commande passée avec succès.", 'commande_id': commande.id})

    # Message classique pour les requêtes normales
    messages.success(request, "Commande passée avec succès.")
    return redirect('confirmation_commande', commande_id=commande.id)











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

    # Debugging logs pour vérification
    print(f"Commande récupérée : {commande}")
    print(f"Lignes commande à afficher : {lignes_commande}, Total : {total}")

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
    with transaction.atomic():  # Assurer une restauration complète en cas d’erreur
        for produit_id, quantite in commande.quantites_initiales.items():
            produit = Produit.objects.select_for_update().get(id=produit_id)
            
            # Vérification pour éviter une double réincrémentation
            if produit.stock + quantite > produit.stock:
                produit.stock += quantite
                produit.save()

        # Marquer la commande comme annulée
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
    ligne_panier = get_object_or_404(LignePanier, id=ligne_panier_id, panier__utilisateur=request.user)
    
    # Réincrémenter le stock du produit
    produit = ligne_panier.produit
    produit.stock += ligne_panier.quantite
    produit.save()
    
    # Supprimer la ligne du panier
    ligne_panier.delete()
    messages.success(request, "Article supprimé du panier.")
    
    return redirect('afficher_panier')




def test_template(request):
    return render(request, 'base.html')