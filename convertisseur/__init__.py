"""Convertisseur : une petite application de bureau pour convertir ses fichiers.

Organisation du dossier :
    fichiers.py     -> outils sur les fichiers (types, tailles, noms…)
    conversions.py  -> les conversions elles-mêmes (PDF, réduction, GIF)
    taches.py       -> exécute les conversions en arrière-plan (fenêtre jamais figée)
    style.py        -> couleurs noir et blanc, mode clair / sombre
    widgets.py      -> éléments d'interface sur mesure (zone de dépôt, boutons…)
    fenetre.py      -> la fenêtre principale et ses écrans
    mise_a_jour.py  -> recherche et installation des nouvelles versions (GitHub)
    application.py  -> démarrage de l'application
"""

NOM_APPLICATION = "Convertisseur"

# Numéro de version : à augmenter avant chaque publication (voir publier.bat)
VERSION = "1.0.0"

# Dépôt GitHub où sont publiées les nouvelles versions (« propriétaire/nom »)
DEPOT_GITHUB = "slazz348-prog/convertisseur"
