/* static/js/panier_confirmation.js */
document.addEventListener('DOMContentLoaded', () => {
    // radios = .liv-option définis dans le template
    const radios   = document.querySelectorAll('.liv-option');
    const spanPrix = document.getElementById('livPrx');   // ligne "Livraison :"
    const spanTot  = document.getElementById('totttc');   // ligne "Total TTC"
    const sousTot  = parseFloat(
        document.getElementById('sousttc').dataset.val        // 499.00, etc.
    );
  
    const fmt = n => n.toFixed(2).replace('.', ',') + ' €';
  
    function majAffichage(prix) {
      spanPrix.textContent = prix === 0 ? 'Gratuite' : fmt(prix);
      spanTot.textContent  = fmt(sousTot + prix);
    }
  
    radios.forEach(r =>
      r.addEventListener('change', e => {
        const prixLiv = parseFloat(e.target.dataset.price);   // 7.90, 0.00, etc.
        majAffichage(prixLiv);
      })
    );
  });
  