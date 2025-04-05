from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Utilisateur

class InscriptionForm(UserCreationForm):
    utiliser_adresse_facturation = forms.BooleanField(
        required=False,
        label="Utiliser comme adresse de facturation",
        initial=True
    )

    class Meta:
        model = Utilisateur
        fields = [
            'email', 'prenom', 'nom', 'societe', 'adresse', 'complement_adresse',
            'code_postal', 'ville', 'pays', 'password1', 'password2'
        ]
        widgets = {
            'adresse': forms.TextInput(attrs={'placeholder': 'Rue + Numéro'}),
            'complement_adresse': forms.TextInput(attrs={'placeholder': "Complément d'adresse (facultatif)"}),
        }

class ModifierProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = [
            'prenom', 'nom', 'email', 'societe', 'adresse', 'complement_adresse',
            'code_postal', 'ville', 'pays'
        ]
