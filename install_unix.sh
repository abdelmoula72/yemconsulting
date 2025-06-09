#!/bin/bash

echo "🚀 Installation de YemTech Pro..."

echo "📍 Détection de Linux/MacOS..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Mise à jour de pip..."
pip install --upgrade pip

echo "📦 Installation des dépendances Python..."
pip install -r requirements.txt

echo "🔄 Application des migrations Django..."
python manage.py migrate

echo "📁 Création des dossiers nécessaires..."
mkdir -p media static

echo "📂 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "✅ Installation terminée !"
echo ""
echo "Pour activer l'environnement virtuel :"
echo "  source venv/bin/activate"
echo ""
echo "⚠️  N'oubliez pas de :"
echo "1. Activer l'environnement virtuel"
echo "  source venv/bin/activate"
echo "2. Créer un superutilisateur si vous le souhaitez avec : python manage.py createsuperuser"
echo "3. Démarrer le serveur avec : python manage.py runserver"
