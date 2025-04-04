import os
import pandas as pd
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from app_yemconsulting.models import Categorie, Produit

print("✅ Script importer_articles.py chargé")

EXCEL_PATH = "articlestfe.xlsx"

class Command(BaseCommand):
    help = "Importer les produits depuis un fichier Excel avec image et description"

    def handle(self, *args, **kwargs):
        print("➡️ Début de la commande handle()")
        
        if not os.path.exists(EXCEL_PATH):
            self.stdout.write(self.style.ERROR(f"❌ Fichier introuvable : {EXCEL_PATH}"))
            return

        df = pd.read_excel(EXCEL_PATH)
        current_parent = None

        for index, row in df.iterrows():
            cat_nom = str(row["Catégorie"]).strip()
            nom = str(row["Nom"]).strip()

            # Grande catégorie
            if pd.isna(row["Nom"]) and pd.isna(row["Prix"]):
                current_parent, _ = Categorie.objects.get_or_create(nom=cat_nom, parent=None)
                self.stdout.write(self.style.NOTICE(f"📁 Grande catégorie détectée : {cat_nom}"))
                continue

            # Sous-catégorie
            sous_cat, _ = Categorie.objects.get_or_create(nom=cat_nom, parent=current_parent)

            # Prix
            prix_brut = row.get("Prix")
            try:
                prix = float(str(prix_brut).replace("€", "").replace(",", ".").strip())
            except Exception:
                self.stdout.write(self.style.WARNING(f"⚠ Prix invalide pour {nom} : {prix_brut}. Défini à 0.0€"))
                prix = 0.0

            produit = Produit(
                nom=nom,
                description=str(row.get("Description")).strip() if not pd.isna(row.get("Description")) else "",
                prix=prix,
                stock=10,
                categorie=sous_cat
            )

            # Image
            image_url = row.get("Image URL")
            if isinstance(image_url, str) and image_url.startswith("http"):
                try:
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        filename = os.path.basename(urlparse(image_url).path)
                        produit.image.save(filename, ContentFile(response.content), save=False)
                    else:
                        self.stdout.write(self.style.WARNING(f"⚠ Erreur image {nom} : statut HTTP {response.status_code}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠ Erreur téléchargement image pour {nom} : {e}"))

            try:
                produit.save()
                self.stdout.write(self.style.SUCCESS(f"✅ Produit importé : {nom}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Erreur en sauvegardant {nom} : {e}"))
