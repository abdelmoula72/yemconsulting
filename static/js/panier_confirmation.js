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

    let typeAdresseAModifier = 'shipping';

    // Vérifier si une nouvelle adresse a été ajoutée (via le paramètre dans l'URL)
    const urlParams = new URLSearchParams(window.location.search);
    const nouvelleAdresseId = urlParams.get('nouvelle_adresse');
    
    if (nouvelleAdresseId) {
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
                adresseContent.innerHTML = `
                    <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                    <div class="adresse-ligne">${data.adresse}</div>
                    ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                    <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                    <div class="adresse-ligne">${data.pays}</div>
                `;

                // Si le toggle est activé, mettre à jour aussi l'adresse de facturation
                if (toggleAdresseFacturation.checked) {
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
                            adresseContentBilling.innerHTML = `
                                <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                <div class="adresse-ligne">${data.adresse}</div>
                                ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                <div class="adresse-ligne">${data.pays}</div>
                            `;
                        }
                    });
                }

                // Activer le bouton de validation de commande
                btnValiderCommande.disabled = false;
            }
        });
        
        // Nettoyer l'URL
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Gestion du toggle d'adresse de facturation
    if (toggleAdresseFacturation) {
        toggleAdresseFacturation.addEventListener('change', function() {
            const isChecked = this.checked;
            blocAdresseFacturation.classList.toggle('d-none', isChecked);
            
            if (isChecked) {
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
                            adresseContent.innerHTML = `
                                <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                <div class="adresse-ligne">${data.adresse}</div>
                                ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                <div class="adresse-ligne">${data.pays}</div>
                            `;
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
                        
                        targetCard.setAttribute('data-adresse-id', adresseId);
                        document.getElementById(targetContentId).innerHTML = `
                            <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                            <div class="adresse-ligne">${data.adresse}</div>
                            ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                            <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                            <div class="adresse-ligne">${data.pays}</div>
                        `;

                        // Si on change l'adresse de livraison et que le toggle est activé,
                        // mettre à jour aussi l'adresse de facturation
                        if (typeAdresseAModifier === 'shipping' && toggleAdresseFacturation.checked) {
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
                                    document.getElementById('adresse-content-billing').innerHTML = `
                                        <div class="adresse-nom">${data.prenom} ${data.nom}</div>
                                        <div class="adresse-ligne">${data.adresse}</div>
                                        ${data.complement ? `<div class="adresse-ligne">${data.complement}</div>` : ''}
                                        <div class="adresse-ligne">${data.code_postal} ${data.ville}</div>
                                        <div class="adresse-ligne">${data.pays}</div>
                                    `;
                                }
                            });
                        }

                        // Activer le bouton de validation de commande si une adresse de livraison est sélectionnée
                        if (typeAdresseAModifier === 'shipping') {
                            btnValiderCommande.disabled = false;
                        }

                        // Fermer la modal
                        const modal = bootstrap.Modal.getInstance(modalAdresses);
                        modal.hide();
                    }
                });
            }
        });
    }

    // Mise à jour du type d'adresse à modifier lors de l'ouverture de la modal
    modalAdresses.addEventListener('show.bs.modal', function(event) {
        const button = event.relatedTarget;
        typeAdresseAModifier = button.dataset.type || 'shipping';
    });

    // Activer/désactiver le bouton Valider en fonction de la sélection
    document.querySelectorAll('input[name="adresseLivraison"]').forEach(radio => {
        radio.addEventListener('change', () => {
            validerAdresse.disabled = false;
        });
    });

    // Gestion du bouton "Ajouter une adresse"
    btnOuvrirAjoutAdresse.addEventListener('click', (e) => {
        e.preventDefault();
        const modal = bootstrap.Modal.getInstance(modalAdresses);
        if (modal) modal.hide();
        
        // Rediriger vers la page d'ajout d'adresse avec retour à la page actuelle
        const returnUrl = encodeURIComponent(window.location.pathname);
        window.location.href = `${btnOuvrirAjoutAdresse.href}?next=${returnUrl}`;
    });

    // Gestion des options de livraison
    const radios = document.querySelectorAll('.liv-option');
    const spanPrix = document.getElementById('livPrx');
    const spanTot = document.getElementById('totttc');
    const sousTot = parseFloat(document.getElementById('sousttc').dataset.val);
    const tva = sousTot * 0.21;
    const totalTTC = sousTot + tva;

    const fmt = n => n.toFixed(2).replace('.', ',') + ' €';

    function majAffichage(prix) {
        spanPrix.textContent = prix === 0 ? 'Gratuite' : fmt(prix);
        spanTot.textContent = fmt(totalTTC + prix);
    }

    radios.forEach(r =>
        r.addEventListener('change', e => {
            const prixLiv = parseFloat(e.target.dataset.price);
            majAffichage(prixLiv);
        })
    );
});
  