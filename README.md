# YEM Consulting

## Description

Site web de YemTech Pro, une entreprise de vente de matériel informatique professionnel.

## Prérequis

### Pour tous les systèmes

- Python (version 3.8 ou supérieure)
- Git

## Installation

1. Clonez le dépôt :

   ```bash
   git clone https://github.com/votre-nom/yemconsulting.git
   cd yemconsulting
   ```

2. Lancez le script d'installation universel :
   ```bash
   python install_launcher.py
   ```
   Ce script détecte automatiquement votre système d'exploitation et exécute le script adapté (Windows ou Linux/MacOS).

**En cas d'erreur ou si le script universel ne fonctionne pas** :  
Vous pouvez lancer manuellement le script correspondant à votre environnement :

- **Windows** :
  ```cmd
  install_windows.bat
  ```
- **Linux / MacOS** :
  ```bash
  bash install_unix.sh
  ```

Le script d'installation va automatiquement :

- Créer un environnement virtuel
- Installer toutes les dépendances Python
- Effectuer les migrations de la base de données
- Créer les dossiers nécessaires (`media`, `static`)
- Collecter les fichiers statiques

## Configuration

Créez un fichier `.env` à la racine du projet avec les variables suivantes :

```env
DEBUG=True
SECRET_KEY=votre_cle_secrete
STRIPE_PUBLIC_KEY=votre_cle_publique_stripe
STRIPE_SECRET_KEY=votre_cle_secrete_stripe
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
├── media/                # Fichiers média uploadés
├── static/               # Fichiers statiques
├── requirements.txt      # Dépendances du projet
├── install_launcher.py   # Script d'installation universel
├── install_windows.bat   # Script d'installation pour Windows
└── install_unix.sh       # Script d'installation pour Linux/MacOS
```

## Contact

Pour toute question ou suggestion, n'hésitez pas à nous contacter.
