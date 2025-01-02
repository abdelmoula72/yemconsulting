$(document).ready(function () {
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

    // Gestion du clic sur une suggestion
    $(document).on("click", ".suggestion-item", function () {
        const produitNom = $(this).text().trim(); // Supprime les espaces avant et après
        $("#search-bar").val(produitNom); // Ajoute le texte sans espaces superflus
        $("#suggestion-box").hide();
    });

    // Cache les suggestions lorsqu'on clique en dehors
    $(document).on("click", function (e) {
        if (!$(e.target).closest("#search-bar, #suggestion-box").length) {
            $("#suggestion-box").hide();
        }
    });
});
