/* static/js/panier_confirmation.js */
document.addEventListener('DOMContentLoaded', () => {
    // Débogage initial
    console.log("Le script panier_confirmation.js est chargé");
    
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
    
    // Débogage des éléments critiques
    console.log("Éléments de prix trouvés:", {
        spanPrix: !!spanPrix,
        spanTot: !!spanTot,
        sousTtcElement: !!sousTtcElement,
        nombreRadios: radios.length
    });
    
    if (radios.length > 0) {
        // Afficher les options de livraison pour le débogage
        radios.forEach((radio, index) => {
            console.log(`Option de livraison ${index}:`, {
                id: radio.id,
                value: radio.value,
                checked: radio.checked,
                dataPrice: radio.getAttribute('data-price'),
                datasetPrice: radio.dataset.price
            });
        });
    }
    
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
        console.log("Mise à jour des prix avec:", livraisonPrice);
        
        // S'assurer que tous les éléments DOM nécessaires sont présents
        if (!spanPrix || !spanTot || !sousTtcElement) {
            console.error("Éléments manquants pour mettre à jour les prix");
            return;
        }

        // Récupérer le prix HT depuis l'attribut data
        const prixHT = parseFloat(sousTtcElement.dataset.val.replace(',', '.'));
        console.log("Prix HT récupéré:", prixHT);
        
        // Calculer le prix TTC (HT * 1.21)
        const prixTTC = roundToInteger(prixHT * 1.21);
        console.log("Prix TTC calculé:", prixTTC);
        
        // Ajouter le prix de livraison
        const totalAvecLivraison = roundToInteger(prixTTC + livraisonPrice);
        console.log("Total avec livraison:", totalAvecLivraison);
        
        // Mettre à jour les affichages
        spanPrix.textContent = livraisonPrice === 0 ? 'Gratuite' : formatPrice(livraisonPrice);
        spanTot.textContent = formatPrice(totalAvecLivraison);
        
        console.log("Affichages mis à jour:", {
            prixLivraison: spanPrix.textContent,
            totalTTC: spanTot.textContent
        });
    }

    // Au chargement, appliquer le formatage initial
    if (radios.length > 0) {
        console.log("Initialisation du formatage des prix");
        
        // Trouver l'option sélectionnée
        const checkedRadio = document.querySelector('.liv-option:checked');
        if (checkedRadio) {
            console.log("Option sélectionnée trouvée:", checkedRadio.id);
            
            // Récupérer le prix de l'option sélectionnée
            const priceAttr = checkedRadio.getAttribute('data-price');
            console.log("Attribut data-price brut:", priceAttr);
            
            // Convertir le prix en nombre
            const initialPrice = parseFloat(priceAttr.replace(',', '.'));
            console.log("Prix initial converti:", initialPrice);
            
            // Appliquer le formatage
            updateDisplayedPrices(initialPrice);
        } else {
            console.warn("Aucune option de livraison n'est sélectionnée");
        }
        
        // Ajouter des écouteurs d'événements pour les changements d'options
        radios.forEach(radio => {
            radio.addEventListener('change', function() {
                console.log("Option de livraison changée:", this.id);
                
                // Prix à partir de l'attribut data-price
                const priceAttr = this.getAttribute('data-price');
                console.log("Attribut data-price:", priceAttr);
                
                const prixLivraison = parseFloat(priceAttr.replace(',', '.'));
                console.log("Prix de livraison converti:", prixLivraison);
                
                const optionChoisie = this.value;
                console.log("Option choisie:", optionChoisie);
                
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
                    } else {
                        console.log("Option de livraison mise à jour avec succès sur le serveur");
                    }
                })
                .catch(error => {
                    console.error("Erreur réseau:", error);
                });
            });
            
            console.log(`Écouteur ajouté à l'option ${radio.id}`);
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
                    // Utiliser une construction progressive du HTML
                    const prenom = data.prenom || '';
                    const nom = data.nom || '';
                    const rue = data.rue || '';
                    const complement = data.complement || '';
                    const code_postal = data.code_postal || '';
                    const ville = data.ville || '';
                    const pays = data.pays || '';
                    
                    let html = `<div class="adresse-nom">${prenom} ${nom}</div>`;
                    html += `<div class="adresse-ligne">${rue}</div>`;
                    
                    if (complement && complement !== 'null' && complement !== 'undefined') {
                        html += `<div class="adresse-ligne">${complement}</div>`;
                    }
                    
                    html += `<div class="adresse-ligne">${code_postal} ${ville}</div>`;
                    html += `<div class="adresse-ligne">${pays}</div>`;
                    
                    adresseContent.innerHTML = html;
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
                                // Utiliser une construction progressive du HTML
                                const prenom = data.prenom || '';
                                const nom = data.nom || '';
                                const rue = data.rue || '';
                                const complement = data.complement || '';
                                const code_postal = data.code_postal || '';
                                const ville = data.ville || '';
                                const pays = data.pays || '';
                                
                                let html = `<div class="adresse-nom">${prenom} ${nom}</div>`;
                                html += `<div class="adresse-ligne">${rue}</div>`;
                                
                                if (complement && complement !== 'null' && complement !== 'undefined') {
                                    html += `<div class="adresse-ligne">${complement}</div>`;
                                }
                                
                                html += `<div class="adresse-ligne">${code_postal} ${ville}</div>`;
                                html += `<div class="adresse-ligne">${pays}</div>`;
                                
                                adresseContentBilling.innerHTML = html;
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
                                // Sécuriser les données avant affichage
                                const prenom = data.prenom || '';
                                const nom = data.nom || '';
                                const rue = data.rue || '';
                                const complement = data.complement || '';
                                const code_postal = data.code_postal || '';
                                const ville = data.ville || '';
                                const pays = data.pays || '';
                                
                                // Construction progressive du HTML
                                let html = `<div class="adresse-nom">${prenom} ${nom}</div>`;
                                html += `<div class="adresse-ligne">${rue}</div>`;
                                
                                if (complement && complement !== 'null' && complement !== 'undefined') {
                                    html += `<div class="adresse-ligne">${complement}</div>`;
                                }
                                
                                html += `<div class="adresse-ligne">${code_postal} ${ville}</div>`;
                                html += `<div class="adresse-ligne">${pays}</div>`;
                                
                                adresseContent.innerHTML = html;
                                
                                console.log('Adresse de facturation mise à jour avec les données de livraison:', {
                                    prenom, nom, rue, complement, code_postal, ville, pays
                                });
                                
                                // Mettre à jour le champ caché d'adresse de facturation
                                const formElement = document.getElementById('confirm-form');
                                if (formElement) {
                                    createOrUpdateHiddenInput(formElement, 'adresse_facturation_id', adresseLivraisonId);
                                }
                            }
                        }
                    })
                    .catch(error => {
                        console.error('Erreur lors de la mise à jour de l\'adresse de facturation:', error);
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
                                // Utiliser une construction progressive du HTML
                                const prenom = data.prenom || '';
                                const nom = data.nom || '';
                                const rue = data.rue || '';
                                const complement = data.complement || '';
                                const code_postal = data.code_postal || '';
                                const ville = data.ville || '';
                                const pays = data.pays || '';
                                
                                let html = `<div class="adresse-nom">${prenom} ${nom}</div>`;
                                html += `<div class="adresse-ligne">${rue}</div>`;
                                
                                if (complement && complement !== 'null' && complement !== 'undefined') {
                                    html += `<div class="adresse-ligne">${complement}</div>`;
                                }
                                
                                html += `<div class="adresse-ligne">${code_postal} ${ville}</div>`;
                                html += `<div class="adresse-ligne">${pays}</div>`;
                                
                                contentElement.innerHTML = html;
                                
                                // Mettre à jour le champ caché correspondant dans le formulaire
                                const formElement = document.getElementById('confirm-form');
                                if (formElement) {
                                    const hiddenFieldName = typeAdresseAModifier === 'shipping' ? 'adresse_livraison_id' : 'adresse_facturation_id';
                                    createOrUpdateHiddenInput(formElement, hiddenFieldName, adresseId);
                                }
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
                                        // Utiliser une construction progressive du HTML
                                        const prenom = data.prenom || '';
                                        const nom = data.nom || '';
                                        const rue = data.rue || '';
                                        const complement = data.complement || '';
                                        const code_postal = data.code_postal || '';
                                        const ville = data.ville || '';
                                        const pays = data.pays || '';
                                        
                                        let html = `<div class="adresse-nom">${prenom} ${nom}</div>`;
                                        html += `<div class="adresse-ligne">${rue}</div>`;
                                        
                                        if (complement && complement !== 'null' && complement !== 'undefined') {
                                            html += `<div class="adresse-ligne">${complement}</div>`;
                                        }
                                        
                                        html += `<div class="adresse-ligne">${code_postal} ${ville}</div>`;
                                        html += `<div class="adresse-ligne">${pays}</div>`;
                                        
                                        billingContent.innerHTML = html;
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
            
            // Récupérer les IDs des adresses sélectionnées depuis les attributs data-adresse-id
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
        console.log(`Champ caché ${name} mis à jour avec la valeur ${value}`);
    }
});
  