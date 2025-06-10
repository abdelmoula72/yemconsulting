@echo off
echo.
echo [INFO] Installation de YemTech Pro...
echo.

echo [ETAPE] Detection de Windows...
python -m venv venv

call .\venv\Scripts\activate

echo [ETAPE] Mise a jour de pip...
python -m pip install --upgrade pip

echo [ETAPE] Installation des dependances Python...
pip install -r requirements.txt

echo [ETAPE] Application des migrations Django...
python manage.py migrate

echo [ETAPE] Creation des dossiers necessaires...
if not exist media mkdir media
if not exist static mkdir static

echo [ETAPE] Collecte des fichiers statiques...
python manage.py collectstatic --noinput

echo.
echo [OK] Installation terminee !
echo.
echo Pour activer l'environnement virtuel :
echo   .\venv\Scripts\activate
echo.
echo N'oubliez pas de :
echo 1. Activer l'environnement virtuel
echo    .\venv\Scripts\activate
echo 2. Creer un superutilisateur si vous le souhaitez avec : python manage.py createsuperuser
echo 3. Demarrer le serveur avec : python manage.py runserver