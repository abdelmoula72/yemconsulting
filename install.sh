#!/bin/bash

# Détection du système d'exploitation
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    echo "Installation sous Windows..."
    python -m venv venv
    ./venv/Scripts/activate
else
    # Linux/MacOS
    echo "Installation sous Linux/MacOS..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Installation des dépendances
pip install --upgrade pip
pip install -r requirements.txt

# Migrations Django
python manage.py migrate

echo "Installation terminée !"
echo "Pour activer l'environnement virtuel :"
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo "  ./venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi 