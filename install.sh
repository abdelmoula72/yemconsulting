#!/bin/bash

# Détection du système d'exploitation
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Installation sous Windows..."
    
    # Vérification de l'installation de GTK3 pour WeasyPrint
    echo "Note: Pour WeasyPrint sous Windows, veuillez installer GTK3"
    echo "Téléchargez-le depuis: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer"
    
    python -m venv venv
    ./venv/Scripts/activate
else
    # Linux/MacOS
    echo "Installation sous Linux/MacOS..."
    
    # Installation des dépendances système pour WeasyPrint
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # MacOS
        echo "Installation des dépendances système pour MacOS..."
        brew install cairo pango gdk-pixbuf libffi
    else
        # Linux
        echo "Installation des dépendances système pour Linux..."
        if [ -x "$(command -v apt-get)" ]; then
            sudo apt-get update
            sudo apt-get install -y build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
        elif [ -x "$(command -v dnf)" ]; then
            sudo dnf install -y redhat-rpm-config python-devel python-pip python-wheel python-cffi libffi-devel cairo pango gdk-pixbuf2
        fi
    fi
    
    python3 -m venv venv
    source venv/bin/activate
fi

# Installation des dépendances Python
echo "Mise à jour de pip..."
pip install --upgrade pip

echo "Installation des dépendances Python..."
pip install -r requirements.txt

# Migrations Django
echo "Application des migrations Django..."
python manage.py migrate

# Création des dossiers statiques et média si nécessaire
echo "Création des dossiers nécessaires..."
mkdir -p media static

echo "Installation terminée !"
echo "Pour activer l'environnement virtuel :"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  ./venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi

echo "Note: N'oubliez pas de configurer les variables d'environnement dans le fichier .env" 