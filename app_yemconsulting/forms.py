from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import Utilisateur, Adresse
import re
from django.core.exceptions import ValidationError

class InscriptionForm(UserCreationForm):
    class Meta:
        model = Utilisateur
        fields = ['email', 'prenom', 'nom', 'password1', 'password2']
        widgets = {
            'prenom': forms.TextInput(attrs={'placeholder': 'ex: Jean'}),
            'nom': forms.TextInput(attrs={'placeholder': 'ex: Dupont'}),
            'email': forms.EmailInput(attrs={'placeholder': 'ex: jean.dupont@email.com'}),
            'password1': forms.PasswordInput(attrs={'placeholder': 'Minimum 8 caractères'}),
            'password2': forms.PasswordInput(attrs={'placeholder': 'Répétez votre mot de passe'}),
        }

    def clean_prenom(self):
        prenom = self.cleaned_data['prenom']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', prenom):
            raise ValidationError("Le prénom ne doit contenir que des lettres.")
        return prenom

    def clean_nom(self):
        nom = self.cleaned_data['nom']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', nom):
            raise ValidationError("Le nom ne doit contenir que des lettres.")
        return nom

    def clean_password1(self):
        password1 = self.cleaned_data['password1']
        if len(password1) < 8:
            raise ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$', password1):
            raise ValidationError("Le mot de passe doit contenir au moins une lettre et un chiffre.")
        return password1

class ModifierProfilForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['prenom', 'nom', 'email']
        labels = {
            'prenom': 'Prénom',
            'nom': 'Nom',
            'email': 'Email',
        }

class DonneesPersonnellesForm(forms.ModelForm):
    class Meta:
        model = Utilisateur
        fields = ['prenom', 'nom', 'email']
        labels = {
            'prenom': 'Prénom',
            'nom': 'Nom',
            'email': 'Email',
        }

class AdresseForm(forms.ModelForm):
    prenom = forms.CharField(label="Prénom", max_length=100, required=True)
    nom = forms.CharField(label="Nom", max_length=100, required=True)
    is_default_shipping = forms.BooleanField(
        required=False,
        label='Définir comme adresse de livraison par défaut',
        help_text=''
    )
    is_default_billing = forms.BooleanField(
        required=False,
        label='Définir comme adresse de facturation par défaut',
        help_text=''
    )

    class Meta:
        model = Adresse
        fields = ['prenom', 'nom', 'adresse', 'complement', 'code_postal', 'ville', 'pays']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user if user else self.instance.utilisateur if self.instance.pk else None
        
        if self.user:
            # Compter le nombre d'adresses actives
            nb_adresses = self.user.adresses.filter(active=True).count()
            
            # Si c'est la première adresse ou modification de la seule adresse
            if nb_adresses == 0 or (self.instance.pk and nb_adresses == 1):
                self.fields['is_default_shipping'].initial = True
                self.fields['is_default_billing'].initial = True
                self.fields['is_default_shipping'].widget.attrs['disabled'] = True
                self.fields['is_default_billing'].widget.attrs['disabled'] = True
            # Si c'est une modification d'adresse par défaut et qu'il n'y en a qu'une
            elif self.instance.pk:
                if self.instance.is_default_shipping and self.user.adresses.filter(is_default_shipping=True, active=True).count() == 1:
                    self.fields['is_default_shipping'].widget.attrs['disabled'] = True
                if self.instance.is_default_billing and self.user.adresses.filter(is_default_billing=True, active=True).count() == 1:
                    self.fields['is_default_billing'].widget.attrs['disabled'] = True

    def clean_prenom(self):
        prenom = self.cleaned_data['prenom']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', prenom):
            raise ValidationError("Le prénom ne doit contenir que des lettres.")
        return prenom

    def clean_nom(self):
        nom = self.cleaned_data['nom']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', nom):
            raise ValidationError("Le nom ne doit contenir que des lettres.")
        return nom

    def clean_code_postal(self):
        code_postal = self.cleaned_data['code_postal']
        # Format belge : 4 chiffres, français : 5 chiffres
        if not re.match(r'^(\d{4}|\d{5})$', code_postal):
            raise ValidationError("Le code postal doit comporter 4 ou 5 chiffres.")
        return code_postal

    def clean_ville(self):
        ville = self.cleaned_data['ville']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', ville):
            raise ValidationError("La ville ne doit contenir que des lettres.")
        return ville

    def clean_pays(self):
        pays = self.cleaned_data['pays']
        if not re.match(r'^[A-Za-zÀ-ÿ\-\s]+$', pays):
            raise ValidationError("Le pays ne doit contenir que des lettres.")
        return pays

    def clean_adresse(self):
        adresse = self.cleaned_data['adresse']
        if len(adresse) < 5:
            raise ValidationError("L'adresse doit contenir au moins 5 caractères.")
        return adresse

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Si c'est la première adresse, forcer les valeurs par défaut
        if self.user and self.user.adresses.filter(active=True).count() == 0:
            instance.is_default_shipping = True
            instance.is_default_billing = True
        else:
            # Sinon utiliser les valeurs du formulaire sauf si disabled
            if not self.fields['is_default_shipping'].widget.attrs.get('disabled'):
                instance.is_default_shipping = self.cleaned_data.get('is_default_shipping', False)
            if not self.fields['is_default_billing'].widget.attrs.get('disabled'):
                instance.is_default_billing = self.cleaned_data.get('is_default_billing', False)
        
        if commit:
            instance.save()
        return instance
