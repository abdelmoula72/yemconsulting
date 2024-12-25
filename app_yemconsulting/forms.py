from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Utilisateur

class InscriptionForm(UserCreationForm):
    class Meta:
        model = Utilisateur
        fields = ['email', 'nom', 'adresse', 'password1', 'password2']

class ModifierProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['nom', 'email', 'adresse']
