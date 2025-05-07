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
    $("#search-bar").on("input", function () {
        const terme = $(this).val().trim();
        const suggestionBox = $("#suggestion-box");

        if (terme.length > 0) {
            $.ajax({
                url: "/suggestions/",
                type: "GET",
                data: { q: terme },
                success: function (data) {
                    suggestionBox.empty();
                    if (data.length > 0) {
                        data.forEach(function (produit) {
                            suggestionBox.append(
                                `<div class="suggestion-item">${produit.nom}</div>`
                            );
                        });
                    } else {
                        suggestionBox.append(
                            `<div class="p-2 text-muted">Aucun résultat</div>`
                        );
                    }
                    suggestionBox.show();
                },
                error: function () {
                    suggestionBox.empty().append(
                        `<div class="p-2 text-danger">Erreur de chargement</div>`
                    );
                    suggestionBox.show();
                },
            });
        } else {
            suggestionBox.hide();
        }
    });

    // 📌 Gestion du clic sur une suggestion
    $(document).on("click", ".suggestion-item", function () {
        const produitNom = $(this).text().trim();
        $("#search-bar").val(produitNom);
        $("#suggestion-box").hide();
    });

    // 📌 Cache les suggestions lorsqu'on clique en dehors
    $(document).on("click", function (e) {
        if (!$(e.target).closest("#search-bar, #suggestion-box").length) {
            $("#suggestion-box").hide();
        }
    });
});
