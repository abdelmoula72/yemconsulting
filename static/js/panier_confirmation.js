/* static/js/panier_confirmation.js */
document.addEventListener('DOMContentLoaded', () => {
    // Éléments DOM
    const modalAdresses = document.getElementById('modalAdresses');
    const validerAdresse = document.getElementById('validerAdresse');
    const blocAdresseFacturation = document.getElementById('blocAdresseFacturation');
    const toggleAdresseFacturation = document.getElementById('toggleAdresseFacturation');
    const carteAdresseLivraison = document.getElementById('carteAdresseLivraison');
    const carteAdresseFacturation = document.getElementById('carteAdresseFacturation');
    const btnOuvrirAjoutAdresse = document.getElementById('btnOuvrirAjoutAdresse');
    const btnValiderCommande = document.getElementById('btnValiderCommande');
    const confirmForm = document.getElementById('confirm-form');

    // NOUVELLE PARTIE - FORMATAGE DES PRIX
    // Récupération des éléments pour les prix
    const spanPrix = document.getElementById('livPrx');
    const spanTot = document.getElementById('totttc');
    const sousTtcElement = document.getElementById('sousttc');
    const radios = document.querySelectorAll('.liv-option');
    
    // Fonction d'arrondi à l'entier le plus proche
    function roundToInteger(num) {
        return Math.round(num);
    }

    // Fonction de formatage de prix - arrondi à l'entier avec ajout de ",00"
    function formatPrice(price) {
        return roundToInteger(price) + ',00 €';
    }

    // Fonction de mise à jour des montants affichés
    function updateDisplayedPrices(livraisonPrice) {
        // S'assurer que tous les éléments DOM nécessaires sont présents
        if (!spanPrix || !spanTot || !sousTtcElement) return;

        // Récupérer le prix HT depuis l'attribut data
        const prixHT = parseFloat(sousTtcElement.dataset.val);
        
        // Calculer le prix TTC (HT * 1.21)
        const prixTTC = roundToInteger(prixHT * 1.21);
        
        // Ajouter le prix de livraison
        const totalAvecLivraison = roundToInteger(prixTTC + livraisonPrice);
        
        // Mettre à jour les affichages
        spanPrix.textContent = livraisonPrice === 0 ? 'Gratuite' : formatPrice(livraisonPrice);
        spanTot.textContent = formatPrice(totalAvecLivraison);
    }

    // Au chargement, appliquer le formatage initial
    if (radios.length > 0) {
        // Trouver l'option sélectionnée
        const checkedRadio = document.querySelector('.liv-option:checked');
        if (checkedRadio) {
            // Récupérer le prix de l'option sélectionnée
            const initialPrice = parseFloat(checkedRadio.dataset.price.replace(',', '.'));
            // Appliquer le formatage
            updateDisplayedPrices(initialPrice);
        }
        
        // Ajouter des écouteurs d'événements pour les changements d'options
        radios.forEach(radio => {
            radio.addEventListener('change', function() {
                // Prix à partir de l'attribut data-price
                const prixLivraison = parseFloat(this.dataset.price.replace(',', '.'));
                const optionChoisie = this.value;
                
                // Mettre à jour l'affichage
                updateDisplayedPrices(prixLivraison);
                
                // Envoyer les données au serveur - Important: utiliser la bonne URL!
                fetch('/confirmation-panier/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: `livraison=${optionChoisie}`
                })
                .then(response => {
                    if (!response.ok) {
                        console.error("Erreur lors de la mise à jour de l'option de livraison");
                    }
                })
                .catch(error => {
                    console.error("Erreur réseau:", error);
                });
            });
        });
    }

    let typeAdresseAModifier = 'shipping';

    // Vérifier si une nouvelle adresse a été ajoutée (via le paramètre dans l'URL)
    const urlParams = new URLSearchParams(window.location.search);
    const nouvelleAdresseId = urlParams.get('nouvelle_adresse');
    
    if (nouvelleAdresseId && carteAdresseLivraison) {
        // Mettre à jour l'adresse de livraison avec la nouvelle adresse
        fetch(`/update-shipping-address/${nouvelleAdresseId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Mettre à jour l'affichage de l'adresse de livraison
                carteAdresseLivraison.setAttribute('data-adresse-id', nouvelleAdresseId);
                const adresseContent = document.getElementById('adresse-content-shipping');
                if (adresseContent) {
                    adresseContent.innerHTML = `
                        <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                        <div class="adresse-ligne">${data.rue}</div>
                        ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                        <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                        <div class="adresse-ligne">${data.pays}</div>
                    `;
                }

                // Si le toggle est activé, mettre à jour aussi l'adresse de facturation
                if (toggleAdresseFacturation && toggleAdresseFacturation.checked && carteAdresseFacturation) {
                    fetch(`/update-billing-address/${nouvelleAdresseId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            carteAdresseFacturation.setAttribute('data-adresse-id', nouvelleAdresseId);
                            const adresseContentBilling = document.getElementById('adresse-content-billing');
                            if (adresseContentBilling) {
                                adresseContentBilling.innerHTML = `
                                    <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                    <div class="adresse-ligne">${data.rue}</div>
                                    ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                    <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                    <div class="adresse-ligne">${data.pays}</div>
                                `;
                            }
                        }
                    });
                }

                // Activer le bouton de validation de commande
                if (btnValiderCommande) {
                    btnValiderCommande.disabled = false;
                }
            }
        });
        
        // Nettoyer l'URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Gestion du toggle d'adresse de facturation
    if (toggleAdresseFacturation) {
        toggleAdresseFacturation.addEventListener('change', function() {
            const isChecked = this.checked;
            if (blocAdresseFacturation) {
                blocAdresseFacturation.classList.toggle('d-none', isChecked);
            }
            
            // Envoyer au serveur l'état du toggle
            fetch('/update-toggle-addresses/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: `is_same=${isChecked}`
            })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Erreur lors de la mise à jour du toggle d\'adresse');
                }
            })
            .catch(error => {
                console.error('Erreur réseau:', error);
            });
            
            if (isChecked && carteAdresseLivraison && carteAdresseFacturation) {
                // Copier l'adresse de livraison vers l'adresse de facturation
                const adresseLivraisonId = carteAdresseLivraison.getAttribute('data-adresse-id');
                if (adresseLivraisonId) {
                    fetch(`/update-billing-address/${adresseLivraisonId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            carteAdresseFacturation.setAttribute('data-adresse-id', adresseLivraisonId);
                            const adresseContent = document.getElementById('adresse-content-billing');
                            if (adresseContent) {
                                adresseContent.innerHTML = `
                                    <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                    <div class="adresse-ligne">${data.rue || 'Pas de rue spécifiée'}</div>
                                    ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                    <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                    <div class="adresse-ligne">${data.pays}</div>
                                `;
                            }
                        }
                    });
                }
            }
        });
    }

    // Gestion de la validation d'adresse dans la modal
    if (validerAdresse) {
        validerAdresse.addEventListener('click', function() {
            const selectedAdresse = document.querySelector('input[name="adresseLivraison"]:checked');
            if (selectedAdresse) {
                const adresseId = selectedAdresse.value;
                let url = `/update-shipping-address/${adresseId}/`;
                
                if (typeAdresseAModifier === 'billing') {
                    url = `/update-billing-address/${adresseId}/`;
                }

                fetch(url, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const targetContent = document.querySelector('.adresse-popup-content', selectedAdresse.parentElement);
                        const targetCard = typeAdresseAModifier === 'shipping' ? carteAdresseLivraison : carteAdresseFacturation;
                        const targetContentId = typeAdresseAModifier === 'shipping' ? 'adresse-content-shipping' : 'adresse-content-billing';
                        
                        if (targetCard) {
                            targetCard.setAttribute('data-adresse-id', adresseId);
                            const contentElement = document.getElementById(targetContentId);
                            if (contentElement) {
                                contentElement.innerHTML = `
                                    <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                    <div class="adresse-ligne">${data.rue || 'Pas de rue spécifiée'}</div>
                                    ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                    <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                    <div class="adresse-ligne">${data.pays}</div>
                                `;
                            }
                        }

                        // Si on change l'adresse de livraison et que le toggle est activé,
                        // mettre à jour aussi l'adresse de facturation
                        if (typeAdresseAModifier === 'shipping' && toggleAdresseFacturation && toggleAdresseFacturation.checked && carteAdresseFacturation) {
                            fetch(`/update-billing-address/${adresseId}/`, {
                                method: 'POST',
                                headers: {
                                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                                }
                            })
                            .then(response => response.json())
                            .then(data => {
                                if (data.success) {
                                    carteAdresseFacturation.setAttribute('data-adresse-id', adresseId);
                                    const billingContent = document.getElementById('adresse-content-billing');
                                    if (billingContent) {
                                        billingContent.innerHTML = `
                                            <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                            <div class="adresse-ligne">${data.rue || 'Pas de rue spécifiée'}</div>
                                            ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                            <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                            <div class="adresse-ligne">${data.pays}</div>
                                        `;
                                    }
                                }
                            });
                        }

                        // Activer le bouton de validation de commande si une adresse de livraison est sélectionnée
                        if (typeAdresseAModifier === 'shipping' && btnValiderCommande) {
                            btnValiderCommande.disabled = false;
                        }

                        // Fermer la modal
                        if (modalAdresses) {
                            const modal = bootstrap.Modal.getInstance(modalAdresses);
                            if (modal) modal.hide();
                        }
                    }
                });
            }
        });
    }

    // Mise à jour du type d'adresse à modifier lors de l'ouverture de la modal
    if (modalAdresses) {
        modalAdresses.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            typeAdresseAModifier = button.dataset.type || 'shipping';
        });
    }

    // Activer/désactiver le bouton Valider en fonction de la sélection
    document.querySelectorAll('input[name="adresseLivraison"]').forEach(radio => {
        radio.addEventListener('change', () => {
            if (validerAdresse) {
                validerAdresse.disabled = false;
            }
        });
    });

    // Gestion du bouton "Ajouter une adresse"
    if (btnOuvrirAjoutAdresse) {
        btnOuvrirAjoutAdresse.addEventListener('click', (e) => {
            e.preventDefault();
            if (modalAdresses) {
                const modal = bootstrap.Modal.getInstance(modalAdresses);
                if (modal) modal.hide();
            }
            
            // Rediriger vers la page d'ajout d'adresse avec retour à la page actuelle
            const returnUrl = encodeURIComponent(window.location.pathname);
            window.location.href = `${btnOuvrirAjoutAdresse.href}?next=${returnUrl}`;
        });
    }

    // AJOUTER : Gestion de la soumission du formulaire pour garantir que les IDs d'adresse sont inclus
    if (confirmForm) {
        confirmForm.addEventListener('submit', function(e) {
            // Prévenir la soumission par défaut
            e.preventDefault();
            
            // Récupérer les IDs des adresses sélectionnées
            const adresseLivraisonId = carteAdresseLivraison ? carteAdresseLivraison.getAttribute('data-adresse-id') : null;
            const adresseFacturationId = carteAdresseFacturation ? carteAdresseFacturation.getAttribute('data-adresse-id') : null;
            
            console.log("Soumission du formulaire avec adresses:", {
                livraison: adresseLivraisonId,
                facturation: adresseFacturationId
            });
            
            // Créer ou mettre à jour les champs cachés pour les adresses
            createOrUpdateHiddenInput(this, 'adresse_livraison_id', adresseLivraisonId);
            createOrUpdateHiddenInput(this, 'adresse_facturation_id', adresseFacturationId);
            
            // Enregistrer les adresses dans la session avant de passer au paiement
            const promises = [];
            
            if (adresseLivraisonId) {
                promises.push(
                    fetch(`/update-shipping-address/${adresseLivraisonId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                );
            }
            
            if (adresseFacturationId) {
                promises.push(
                    fetch(`/update-billing-address/${adresseFacturationId}/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                        }
                    })
                );
            }
            
            // Attendre que toutes les requêtes soient terminées avant de soumettre le formulaire
            Promise.all(promises)
                .then(() => {
                    console.log("Adresses mises à jour dans la session, soumission du formulaire...");
                    // Soumettre le formulaire
                    this.submit();
                })
                .catch(error => {
                    console.error("Erreur lors de la mise à jour des adresses:", error);
                    // Soumettre quand même le formulaire
                    this.submit();
                });
        });
    }
    
    // Fonction utilitaire pour créer ou mettre à jour un champ caché
    function createOrUpdateHiddenInput(form, name, value) {
        let input = form.querySelector(`input[name="${name}"]`);
        if (!input) {
            input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            form.appendChild(input);
        }
        input.value = value || '';
    }
});
  