#!/bin/bash

echo "🚀 Installation de YemTech Pro..."

# Détection du système d'exploitation
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "📍 Détection de Windows..."
    python -m venv venv
    ./venv/Scripts/activate
else
    # Linux/MacOS
    echo "📍 Détection de Linux/MacOS..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Installation des dépendances Python
echo "📦 Mise à jour de pip..."
pip install --upgrade pip

echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

# Migrations Django
echo "🔄 Application des migrations Django..."
python manage.py migrate

# Création des dossiers statiques et média
echo "📁 Création des dossiers nécessaires..."
mkdir -p media static

# Collecte des fichiers statiques
echo "📂 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "✅ Installation terminée !"
echo ""
echo "Pour activer l'environnement virtuel :"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  ./venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi

echo ""
echo "⚠️  N'oubliez pas de :"
echo "1. Activer l'environnement virtuel"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  ./venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi
echo "2. Créer un superutilisateur si vous le souhaitez avec : python manage.py createsuperuser"
echo "3. Demarrer le serveur avec : python manage.py runserver"