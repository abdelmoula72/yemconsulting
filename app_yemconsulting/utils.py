from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

def envoyer_email_confirmation(commande):
    sujet = f"Confirmation de votre commande #{commande.id}"
    message = render_to_string('emails/confirmation_commande.html', {
        'commande': commande,
        'utilisateur': commande.utilisateur,
    })
    destinataire = [commande.utilisateur.email]

    send_mail(
        sujet,
        message,
        settings.DEFAULT_FROM_EMAIL,
        destinataire,
        fail_silently=False,
    )
