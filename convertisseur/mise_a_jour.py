"""Mises à jour automatiques depuis GitHub.

Principe :
    1. Au démarrage, on demande discrètement à GitHub quelle est la dernière
       version publiée (la dernière « Release » du dépôt).
    2. Si elle est plus récente que la nôtre, un bandeau le propose.
    3. Si l'utilisateur accepte, on télécharge le fichier .zip de la nouvelle
       version, on le décompresse dans un dossier temporaire, puis un petit
       script PowerShell attend que l'application se ferme, remplace les
       fichiers et relance l'application.

Les fonctions longues suivent la même règle que conversions.py :
elles reçoivent progression(pourcentage, texte) et arret().
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from . import DEPOT_GITHUB, NOM_APPLICATION, VERSION
from .conversions import ConversionAnnulee, ErreurConversion

journal = logging.getLogger(__name__)

ADRESSE_API = f"https://api.github.com/repos/{DEPOT_GITHUB}/releases/latest"
PAGE_VERSIONS = f"https://github.com/{DEPOT_GITHUB}/releases/latest"
ENTETES = {"User-Agent": f"{NOM_APPLICATION}/{VERSION}", "Accept": "application/vnd.github+json"}


def version_en_nombres(texte: str) -> tuple:
    """« v1.2.0 » -> (1, 2, 0), pour pouvoir comparer deux versions."""
    morceaux = []
    for morceau in texte.strip().lstrip("vV").split("."):
        chiffres = "".join(c for c in morceau if c.isdigit())
        morceaux.append(int(chiffres) if chiffres else 0)
    while len(morceaux) < 3:
        morceaux.append(0)
    return tuple(morceaux)


def est_installee() -> bool:
    """Vrai si on tourne depuis le .exe (et pas depuis le code Python)."""
    return getattr(sys, "frozen", False)


def dossier_installation() -> Path:
    """Le dossier qui contient Convertisseur.exe."""
    return Path(sys.executable).resolve().parent


def verifier(progression=None, arret=None) -> dict | None:
    """Demande à GitHub la dernière version.

    Renvoie {"version", "notes", "zip", "taille"} si une version PLUS RÉCENTE
    existe, sinon None. Ne lève jamais d'erreur : sans Internet, on se tait.
    """
    try:
        requete = urllib.request.Request(ADRESSE_API, headers=ENTETES)
        with urllib.request.urlopen(requete, timeout=10) as reponse:
            donnees = json.load(reponse)
    except Exception as erreur:
        journal.warning("Vérification des mises à jour impossible : %s", erreur)
        return None

    etiquette = donnees.get("tag_name", "")
    if version_en_nombres(etiquette) <= version_en_nombres(VERSION):
        return None

    # On cherche le fichier .zip joint à la version
    fichier_zip = next(
        (a for a in donnees.get("assets", []) if a.get("name", "").lower().endswith(".zip")),
        None,
    )
    return {
        "version": etiquette.lstrip("vV"),
        "notes": (donnees.get("body") or "").strip(),
        "zip": fichier_zip.get("browser_download_url") if fichier_zip else None,
        "taille": fichier_zip.get("size", 0) if fichier_zip else 0,
    }


def telecharger_et_preparer(adresse_zip: str, progression, arret) -> dict:
    """Télécharge le .zip de la nouvelle version et le décompresse.

    Renvoie {"dossier": dossier décompressé, prêt à remplacer l'ancien}.
    """
    if not est_installee():
        raise ErreurConversion(
            "La mise à jour automatique ne marche que depuis l'application installée (.exe)."
        )

    # Peut-on écrire dans le dossier de l'application ?
    test = dossier_installation() / ".test_ecriture"
    try:
        test.write_text("ok")
        test.unlink()
    except OSError:
        raise ErreurConversion(
            "Impossible de mettre à jour : le dossier de l'application est protégé en écriture.\n"
            "Télécharge la nouvelle version à la main depuis GitHub."
        )

    temporaire = Path(tempfile.mkdtemp(prefix="convertisseur_maj_"))
    archive = temporaire / "mise_a_jour.zip"
    try:
        requete = urllib.request.Request(adresse_zip, headers={"User-Agent": ENTETES["User-Agent"]})
        with urllib.request.urlopen(requete, timeout=30) as reponse, open(archive, "wb") as sortie:
            total = int(reponse.headers.get("Content-Length") or 0)
            recu = 0
            while True:
                if arret():
                    raise ConversionAnnulee()
                bloc = reponse.read(256 * 1024)
                if not bloc:
                    break
                sortie.write(bloc)
                recu += len(bloc)
                if total:
                    progression(int(recu * 90 / total), "Téléchargement…")
                else:
                    progression(-1, "Téléchargement…")

        progression(92, "Décompression…")
        dossier = temporaire / "nouvelle_version"
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dossier)
        archive.unlink()

        # Le .zip contient un dossier « Convertisseur » avec Convertisseur.exe dedans
        exes = list(dossier.glob("**/Convertisseur.exe"))
        if not exes:
            raise ErreurConversion("Le fichier de mise à jour est incomplet.")
        progression(100, "Prêt")
        return {"dossier": exes[0].parent, "temporaire": temporaire}

    except (ErreurConversion, ConversionAnnulee):
        shutil.rmtree(temporaire, ignore_errors=True)
        raise
    except zipfile.BadZipFile:
        shutil.rmtree(temporaire, ignore_errors=True)
        raise ErreurConversion("Le fichier de mise à jour est abîmé. Réessaie plus tard.")
    except OSError as erreur:
        shutil.rmtree(temporaire, ignore_errors=True)
        journal.exception("Téléchargement de la mise à jour")
        raise ErreurConversion(
            f"Le téléchargement a échoué. Vérifie ta connexion Internet.\n\nDétail : {erreur}"
        )


# Script PowerShell qui remplace les fichiers une fois l'application fermée
SCRIPT_REMPLACEMENT = r"""
param([int]$Processus, [string]$Source, [string]$Destination, [string]$Temporaire)
# 1. Attendre que Convertisseur soit bien fermé
Wait-Process -Id $Processus -Timeout 60 -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500
# 2. Copier la nouvelle version par-dessus l'ancienne (quelques essais si un fichier est occupé)
robocopy $Source $Destination /E /R:10 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
# 3. Relancer l'application et faire le ménage
Start-Process -FilePath (Join-Path $Destination 'Convertisseur.exe')
Remove-Item -LiteralPath $Temporaire -Recurse -Force -ErrorAction SilentlyContinue
"""


def lancer_remplacement(preparation: dict):
    """Démarre le script de remplacement. L'application doit se fermer juste après."""
    destination = dossier_installation()
    # Sécurité : on ne remplace que le dossier d'une vraie installation de Convertisseur
    if not ((destination / "Convertisseur.exe").exists() and (destination / "_internal").is_dir()):
        raise ErreurConversion("Dossier d'installation non reconnu : mise à jour annulée.")

    script = Path(preparation["temporaire"]) / "remplacer.ps1"
    script.write_text(SCRIPT_REMPLACEMENT, encoding="utf-8-sig")
    # Le script tourne sans fenêtre et indépendamment de l'application
    drapeaux = (getattr(subprocess, "CREATE_NO_WINDOW", 0)
                | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    subprocess.Popen(
        [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden", "-File", str(script),
            "-Processus", str(os.getpid()),
            "-Source", str(preparation["dossier"]),
            "-Destination", str(destination),
            "-Temporaire", str(preparation["temporaire"]),
        ],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=drapeaux, close_fds=True,
    )
