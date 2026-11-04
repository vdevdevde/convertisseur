"""Petits outils sur les fichiers : reconnaître leur type, afficher une taille,
trouver un nom libre, ouvrir l'explorateur Windows…"""

import os
import re
import subprocess
import sys
from pathlib import Path

# Extensions reconnues (toujours en minuscules)
EXTENSIONS_IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
EXTENSIONS_VIDEOS = {".mp4", ".mov", ".avi"}


def cle_naturelle(chemin: Path):
    """Clé de tri « naturel » : photo2 vient avant photo10."""
    morceaux = re.split(r"(\d+)", chemin.name.lower())
    return [int(m) if m.isdigit() else m for m in morceaux]


def trier_fichiers(chemins):
    """Range les chemins reçus en trois listes : images, vidéos, ignorés.

    Si on dépose un dossier, on prend les fichiers qu'il contient directement.
    Les doublons sont retirés.
    """
    images, videos, ignores = [], [], []
    deja_vus = set()

    def ranger(chemin: Path):
        cle = str(chemin.resolve()).lower()
        if cle in deja_vus:
            return
        deja_vus.add(cle)
        extension = chemin.suffix.lower()
        if extension in EXTENSIONS_IMAGES:
            images.append(chemin)
        elif extension in EXTENSIONS_VIDEOS:
            videos.append(chemin)
        else:
            ignores.append(chemin)

    for brut in chemins:
        chemin = Path(brut)
        try:
            if chemin.is_dir():
                for enfant in sorted(chemin.iterdir(), key=cle_naturelle):
                    if enfant.is_file():
                        ranger(enfant)
            elif chemin.is_file():
                ranger(chemin)
        except OSError:
            ignores.append(chemin)

    images.sort(key=cle_naturelle)
    videos.sort(key=cle_naturelle)
    return images, videos, ignores


def taille_lisible(octets: int) -> str:
    """Transforme un nombre d'octets en texte lisible : « 4,2 Mo »."""
    valeur = float(octets)
    for unite in ("o", "Ko", "Mo", "Go"):
        if valeur < 1024 or unite == "Go":
            break
        valeur /= 1024
    if unite in ("o", "Ko") or valeur >= 10:
        texte = f"{valeur:.0f}"
    else:
        texte = f"{valeur:.1f}".replace(".", ",").replace(",0", "")
    return f"{texte} {unite}"


def duree_lisible(secondes: float) -> str:
    """12.5 -> « 0:12 », 75 -> « 1:15 »."""
    secondes = int(round(secondes))
    minutes, secondes = divmod(secondes, 60)
    heures, minutes = divmod(minutes, 60)
    if heures:
        return f"{heures}:{minutes:02d}:{secondes:02d}"
    return f"{minutes}:{secondes:02d}"


def nombre(n: int, singulier: str, pluriel: str | None = None) -> str:
    """nombre(1, "photo") -> « 1 photo », nombre(3, "photo") -> « 3 photos »."""
    if n > 1:
        return f"{n} {pluriel or singulier + 's'}"
    return f"{n} {singulier}"


def chemin_unique(chemin: Path) -> Path:
    """Renvoie un chemin qui n'existe pas encore, pour ne JAMAIS écraser un fichier.

    « images.pdf » existe déjà -> « images (2).pdf », puis « images (3).pdf »…
    """
    if not chemin.exists():
        return chemin
    numero = 2
    while True:
        candidat = chemin.with_name(f"{chemin.stem} ({numero}){chemin.suffix}")
        if not candidat.exists():
            return candidat
        numero += 1


def chemin_ressource(nom: str) -> Path:
    """Chemin d'un fichier du dossier « ressources » (icône…).

    Fonctionne aussi bien en lançant le script Python que depuis le .exe
    fabriqué par PyInstaller (qui range ses fichiers dans sys._MEIPASS).
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "ressources" / nom


def ouvrir_dans_explorateur(chemin: Path):
    """Ouvre l'explorateur Windows : sur le fichier (sélectionné) ou sur le dossier."""
    chemin = Path(chemin)
    if sys.platform != "win32":
        return
    if chemin.is_file():
        subprocess.Popen(["explorer", "/select,", str(chemin)])
    else:
        os.startfile(str(chemin))
