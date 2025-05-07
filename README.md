# YEM Consulting

## Description
Site web de YEM Consulting, une entreprise de conseil en informatique.

## Prérequis
- Python (version 3.8 ou supérieure)
- pip (gestionnaire de paquets Python)
- Git Bash (pour Windows) ou Terminal (pour Linux/MacOS)

## Installation

### Installation automatique (recommandée)
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

### Installation manuelle
Si vous préférez installer manuellement :

1. Clonez le dépôt :
```bash
git clone https://github.com/votre-nom/yemconsulting.git
cd yemconsulting
```

2. Créez et activez un environnement virtuel :
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/MacOS
python -m venv venv
source venv/bin/activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Effectuez les migrations de la base de données :
```bash
python manage.py migrate
```

## Lancement du projet

### En mode développement
Pour lancer le serveur de développement :
```bash
python manage.py runserver
```
Le site sera accessible à l'adresse : `http://localhost:8000`

### Création d'un superutilisateur
Pour créer un compte administrateur :
```bash
python manage.py createsuperuser
```

## Technologies utilisées
- Django
- Python
- SQLite (base de données par défaut)
- HTML/CSS
- JavaScript

## Structure du projet
```
yemconsulting/
├── yemconsulting/        # Configuration principale du projet Django
│   ├── settings.py       # Paramètres du projet
│   ├── urls.py          # URLs principales
│   ├── wsgi.py          # Configuration WSGI
│   └── asgi.py          # Configuration ASGI
│
├── app_yemconsulting/    # Application principale
│   ├── admin.py         # Configuration de l'interface d'administration
│   ├── models.py        # Modèles de données
│   ├── views.py         # Vues et logique métier
│   ├── forms.py         # Formulaires
│   ├── urls.py          # URLs de l'application
│   ├── templates/       # Templates HTML
│   ├── utils/           # Utilitaires
│   └── management/      # Commandes personnalisées
│
└── requirements.txt      # Dépendances du projet
```

## Contact
Pour toute question ou suggestion, n'hésitez pas à nous contacter. 