import pandas as pd
import os
import requests
from urllib.parse import urlparse
import re

EXCEL_PATH = "articlestfe.xlsx"
MEDIA_ROOT = "media/produits"

def slugify(value):
    return re.sub(r'[^\w\-_.]', '_', str(value))

df = pd.read_excel(EXCEL_PATH)

for _, row in df.iterrows():
    categorie = str(row['Catégorie']).strip()
    image_url = row['Image URL']

    if pd.isna(image_url) or image_url == "N/A":
        continue

    cat_folder = os.path.join(MEDIA_ROOT, slugify(categorie))
    os.makedirs(cat_folder, exist_ok=True)

    filename = os.path.basename(urlparse(image_url).path)
    image_path = os.path.join(cat_folder, filename)

    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"✅ Téléchargée : {image_path}")
        else:
            print(f"❌ Erreur {response.status_code} : {image_url}")
    except Exception as e:
        print(f"⚠️ Exception {image_url} -> {e}")
