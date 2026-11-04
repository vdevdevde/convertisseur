"""Dessine l'icône de l'application : un carré noir arrondi avec deux flèches blanches (⇄).

Produit ressources/icone.ico (pour Windows) et ressources/icone.png.
Lancement :  .venv\\Scripts\\python.exe outils\\creer_icone.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

DOSSIER = Path(__file__).resolve().parent.parent / "ressources"
TAILLE = 1024  # on dessine en grand, puis on réduit : les bords sont plus nets


def dessiner() -> Image.Image:
    s = TAILLE
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)

    # Fond : carré noir aux coins arrondis
    d.rounded_rectangle((0.04 * s, 0.04 * s, 0.96 * s, 0.96 * s), radius=0.2 * s, fill="black")

    epaisseur = int(0.075 * s)
    blanc = "white"

    # Flèche du haut, vers la droite
    y = 0.39 * s
    d.line((0.25 * s, y, 0.64 * s, y), fill=blanc, width=epaisseur)
    d.polygon([(0.77 * s, y), (0.60 * s, y - 0.12 * s), (0.60 * s, y + 0.12 * s)], fill=blanc)

    # Flèche du bas, vers la gauche
    y = 0.63 * s
    d.line((0.36 * s, y, 0.75 * s, y), fill=blanc, width=epaisseur)
    d.polygon([(0.23 * s, y), (0.40 * s, y - 0.12 * s), (0.40 * s, y + 0.12 * s)], fill=blanc)
    return image


if __name__ == "__main__":
    DOSSIER.mkdir(exist_ok=True)
    icone = dessiner()
    icone.resize((256, 256), Image.Resampling.LANCZOS).save(DOSSIER / "icone.png")
    icone.save(DOSSIER / "icone.ico",
               sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Icône créée dans", DOSSIER)
