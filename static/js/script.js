$(document).ready(function () {
    $(".add-to-cart-form").off("submit").on("submit", function (e) {
        e.preventDefault(); // ✅ Empêche le rechargement de la page

        let form = $(this);
        let url = form.attr("action");
        let formData = form.serialize();
        let csrfToken = $("input[name=csrfmiddlewaretoken]").val();  // ✅ Récupération du token CSRF

        $.ajax({
            type: "POST",
            url: url,
            data: formData,
            dataType: "json",
            headers: { "X-CSRFToken": csrfToken },
            success: function (response) {
                console.log("✅ Réponse AJAX reçue:", response);  // 🔍 Vérification dans la console

                if (response.success) {
                    $("#cart-count").text(response.total_quantite).show();

                    let messageBox = $("#cart-message");
                    messageBox.text(response.message);
                    messageBox.fadeIn().delay(2000).fadeOut();
                } else {
                    alert(response.message);
                }
            },
            error: function (xhr, status, error) {
                console.log("❌ Erreur AJAX:", xhr.responseText); // 🔍 Log l'erreur pour debug
                alert("Erreur lors de l'ajout au panier.");
            }
        });
    });

    // 📌 Gestion du champ de recherche avec autocomplétion
    const searchBar = $('#search-bar');
    const resultsContainer = $('<div>')
        .addClass('position-absolute top-100 start-0 w-100 bg-white border rounded mt-1 shadow-sm')
        .attr('id', 'suggestion-box')
        .css('z-index', '1050')
        .hide();
    
    searchBar.after(resultsContainer);

    searchBar.on('input', function() {
        const query = $(this).val().trim();
        if (query.length >= 2) {
            $.get('/suggestions/', { q: query }, function(data) {
                resultsContainer.empty();
                if (data.length > 0) {
                    data.forEach(function(item) {
                        const suggestionDiv = $(`
                            <div class="suggestion-item p-2 d-flex justify-content-between align-items-center">
                                <div>
                                    <div class="fw-bold">${item.nom}</div>
                                    ${item.categorie ? `<small class="text-muted">${item.categorie}</small>` : ''}
                                </div>
                                <div class="text-end">
                                    <span class="badge bg-primary">${item.prix} €</span>
                                </div>
                            </div>
                        `).data('product-id', item.id);

                        suggestionDiv
                            .css('cursor', 'pointer')
                            .hover(
                                function() { $(this).addClass('bg-light'); },
                                function() { $(this).removeClass('bg-light'); }
                            )
                            .click(function() {
                                window.location.href = `/produit/${$(this).data('product-id')}/`;
                            });

                        resultsContainer.append(suggestionDiv);
                    });
                    resultsContainer.show();
                } else {
                    resultsContainer.hide();
                }
            });
        } else {
            resultsContainer.hide();
        }
    });

    $(document).click(function(e) {
        if (!$(e.target).closest('#search-bar, #suggestion-box').length) {
            resultsContainer.hide();
        }
    });

    // Gestion des touches du clavier
    searchBar.on('keydown', function(e) {
        const items = resultsContainer.find('.suggestion-item');
        const current = resultsContainer.find('.bg-light');
        
        switch(e.keyCode) {
            case 40: // Flèche bas
                e.preventDefault();
                if (current.length === 0) {
                    items.first().addClass('bg-light');
                } else {
                    current.removeClass('bg-light')
                          .next('.suggestion-item')
                          .addClass('bg-light');
                }
                break;
                
            case 38: // Flèche haut
                e.preventDefault();
                if (current.length === 0) {
                    items.last().addClass('bg-light');
                } else {
                    current.removeClass('bg-light')
                          .prev('.suggestion-item')
                          .addClass('bg-light');
                }
                break;
                
            case 13: // Touche Entrée
                if (current.length > 0) {
                    e.preventDefault();
                    const productId = current.data('product-id');
                    if (productId) {
                        window.location.href = `/produit/${productId}/`;
                    }
                }
                break;
                
            case 27: // Touche Échap
                resultsContainer.hide();
                break;
        }
    });
});
