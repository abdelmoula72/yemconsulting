$(document).ready(function () {
    // Gestion de l'ajout au panier avec AJAX
    $(".add-to-cart-form").submit(function (event) {
        event.preventDefault(); // Empêche le rechargement de la page
        let form = $(this);
        let url = form.attr("action");
        let data = form.serialize();

        $.ajax({
            url: url,
            type: "POST",
            data: data,
            success: function (response) {
                if (response.success) {
                    alert(response.message); // Affiche un message de succès
                } else {
                    alert("Une erreur est survenue.");
                }
            },
            error: function (xhr) {
                let error = JSON.parse(xhr.responseText);
                alert(error.message || "Une erreur s'est produite.");
            },
        });
    });
});


    // Mise à jour des quantités dans le panier
    $(".update-quantity-form").submit(function (event) {
        event.preventDefault();
        let form = $(this);
        let url = form.attr("action");
        let data = form.serialize();

        $.ajax({
            url: url,
            type: "POST",
            data: data,
            success: function (response) {
                if (response.success) {
                    // Met à jour le sous-total et le total
                    form.closest("tr").find(".sous-total").text(response.sous_total + " €");
                    $("#total").text("Total : " + response.total + " €");
                } else {
                    alert(response.message); // Affiche le message d'erreur
                }
            },
            error: function (xhr) {
                let error = JSON.parse(xhr.responseText);
                alert(error.message || "Une erreur s'est produite.");
            },
        });
    });

    // Suppression d'un produit du panier
    $(".delete-item-form").submit(function (event) {
        event.preventDefault();
        if (!confirm("Êtes-vous sûr de vouloir supprimer cet article ?")) {
            return;
        }
        let form = $(this);
        let url = form.attr("action");

        $.ajax({
            url: url,
            type: "POST",
            data: { csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val() },
            success: function (response) {
                if (response.success) {
                    form.closest("tr").remove(); // Supprime la ligne du tableau
                    $("#total").text("Total : " + response.total + " €"); // Met à jour le total
                } else {
                    alert(response.message);
                }
            },
            error: function (xhr) {
                let error = JSON.parse(xhr.responseText);
                alert(error.message || "Une erreur s'est produite.");
            },
        });
    });


$(document).ready(function () {
    $("#passer-commande").click(function (event) {
        event.preventDefault();

        let url = $(this).attr("href");

        $.ajax({
            url: url,
            type: "POST",
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
            success: function (response) {
                alert(response.message);
                window.location.href = "/confirmation_commande/" + response.commande_id + "/";
            },
            error: function (xhr) {
                let response = JSON.parse(xhr.responseText);
                alert(response.message);
            },
        });
    });
});
