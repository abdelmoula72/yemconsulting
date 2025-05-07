# YEM Consulting

## Description
Site web de YemTech Pro, une entreprise de vente de matériel informatique professionnel.

## Prérequis

### Pour tous les systèmes
- Python (version 3.8 ou supérieure)
- Git

### Dépendances système supplémentaires

#### Windows
- Git Bash

## Installation

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-nom/yemconsulting.git
cd yemconsulting
```

2. Lancez le script d'installation :
```bash
# Windows (avec Git Bash)
./install.sh

# Linux/MacOS
bash install.sh
```

Le script d'installation va automatiquement :
- Créer un environnement virtuel
- Installer toutes les dépendances Python
- Effectuer les migrations de la base de données
- Créer les dossiers nécessaires (media, static)

## Configuration

Créez un fichier `.env` à la racine du projet avec les variables suivantes :
```env
DEBUG=True
SECRET_KEY=votre_clé_secrète
STRIPE_PUBLIC_KEY=votre_clé_publique_stripe
STRIPE_SECRET_KEY=votre_clé_secrète_stripe
```

## Technologies utilisées
- Django 4.2+ : Framework web Python
- Django Widget Tweaks : Personnalisation des formulaires
- Pillow : Traitement d'images
- Requests : Gestion des requêtes HTTP
- Stripe : Système de paiement
- Django Extensions : Outils de développement supplémentaires
- ReportLab : Génération de documents PDF

## Structure du projet
```
yemconsulting/
├── yemconsulting/        # Configuration principale du projet Django
├── app_yemconsulting/    # Application principale
├── media/               # Fichiers média uploadés
├── static/              # Fichiers statiques
├── requirements.txt     # Dépendances du projet
└── install.sh          # Script d'installation automatique
```

## Contact
Pour toute question ou suggestion, n'hésitez pas à nous contacter. 