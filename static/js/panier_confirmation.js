/* static/js/panier_confirmation.js */
document.addEventListener('DOMContentLoaded', () => {
    // radios = .liv-option définis dans le template
    const radios   = document.querySelectorAll('.liv-option');
    const spanPrix = document.getElementById('livPrx');   // ligne "Livraison :"
    const spanTot  = document.getElementById('totttc');   // ligne "Total TTC"
    const sousTot  = parseFloat(
        document.getElementById('sousttc').dataset.val        // total HT
    );
    const tva = sousTot * 0.21; // TVA 21%
    const totalTTC = sousTot + tva; // Total TTC sans livraison
  
    const fmt = n => n.toFixed(2).replace('.', ',') + ' €';
  
    function majAffichage(prix) {
      spanPrix.textContent = prix === 0 ? 'Gratuite' : fmt(prix);
      spanTot.textContent  = fmt(totalTTC + prix); // Ajoute le prix de la livraison au total TTC
    }
  
    radios.forEach(r =>
      r.addEventListener('change', e => {
        const prixLiv = parseFloat(e.target.dataset.price);   // 7.90, 0.00, etc.
        majAffichage(prixLiv);
      })
    );

    // Gestion de la validation du formulaire
    const btnValiderCommande = document.getElementById('btnValiderCommande');
    const carteAdresseLivraison = document.getElementById('carteAdresseLivraison');
    
    function verifierAdresse() {
      const adresseId = carteAdresseLivraison.getAttribute('data-adresse-id');
      btnValiderCommande.disabled = !adresseId;
    }

    // Vérifier l'état initial
    verifierAdresse();

    // Mettre à jour le bouton quand une adresse est sélectionnée
    const validerAdresse = document.getElementById('validerAdresse');
    if (validerAdresse) {
      validerAdresse.addEventListener('click', () => {
        setTimeout(verifierAdresse, 500); // Attendre que l'adresse soit mise à jour
      });
    }
});
  