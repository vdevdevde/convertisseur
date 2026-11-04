"""Les conversions elles-mêmes : créer un PDF, réduire des photos, faire un GIF.

Ce fichier ne contient AUCUNE interface graphique. Chaque fonction reçoit :
    - progression(pourcentage, texte) : pour dire où on en est
      (pourcentage = -1 quand on ne peut pas savoir) ;
    - arret() : renvoie True si l'utilisateur a demandé d'annuler.

En cas de problème, on lève ErreurConversion avec un message clair en français.

RÈGLE D'OR : les fichiers d'origine ne sont JAMAIS modifiés ni supprimés.
On les ouvre seulement en lecture, et on écrit toujours dans de NOUVEAUX fichiers.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

from .fichiers import chemin_unique

journal = logging.getLogger(__name__)

# Lecture des photos HEIC (iPhone) grâce à pillow-heif
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIC_DISPONIBLE = True
except Exception:  # pragma: no cover - si la bibliothèque manque
    HEIC_DISPONIBLE = False

# Autorise les très grandes photos (jusqu'à 250 mégapixels)
Image.MAX_IMAGE_PIXELS = 250_000_000

# Dans un PDF, on limite le plus grand côté d'une image (≈ A4 à 300 dpi)
COTE_MAX_PDF = 3508
# Longueur d'une page A4 en pouces (sert à donner une taille de page raisonnable)
POUCES_A4 = 11.69

# Sous Windows : empêche FFmpeg d'ouvrir une fenêtre noire de console
SANS_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class ErreurConversion(Exception):
    """Erreur dont le message est destiné à l'utilisateur (en français)."""


class ConversionAnnulee(Exception):
    """L'utilisateur a cliqué sur « Annuler »."""


def _verifier_arret(arret):
    if arret():
        raise ConversionAnnulee()


# ---------------------------------------------------------------------------
# Outils pour les images
# ---------------------------------------------------------------------------

def ouvrir_image(chemin: Path) -> Image.Image:
    """Ouvre une image (en lecture seule) et la remet à l'endroit.

    Les photos de téléphone sont souvent enregistrées « couchées » avec une
    indication de rotation : exif_transpose applique cette rotation.
    On renvoie une COPIE en mémoire : le fichier d'origine est refermé aussitôt.
    """
    nom = Path(chemin).name
    try:
        with Image.open(chemin) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
            return image
    except FileNotFoundError:
        raise ErreurConversion(f"Le fichier « {nom} » est introuvable. A-t-il été déplacé ?")
    except PermissionError:
        raise ErreurConversion(f"Impossible d'ouvrir « {nom} » : accès refusé.")
    except Image.DecompressionBombError:
        raise ErreurConversion(f"L'image « {nom} » est beaucoup trop grande pour être traitée.")
    except MemoryError:
        raise ErreurConversion(f"Pas assez de mémoire pour ouvrir « {nom} ».")
    except Exception:
        journal.exception("Lecture impossible : %s", chemin)
        raise ErreurConversion(f"Impossible de lire l'image « {nom} ». Elle est peut-être abîmée.")


def a_de_la_transparence(image: Image.Image) -> bool:
    """Vrai si l'image contient vraiment des zones transparentes."""
    if image.mode in ("RGBA", "LA", "PA") or (image.mode == "P" and "transparency" in image.info):
        alpha = image.convert("RGBA").getchannel("A")
        return alpha.getextrema()[0] < 255
    return False


def en_rgb(image: Image.Image) -> Image.Image:
    """Convertit en couleurs RGB classiques. La transparence devient du blanc."""
    if image.mode == "RGB":
        return image
    if a_de_la_transparence(image):
        rgba = image.convert("RGBA")
        fond = Image.new("RGB", rgba.size, (255, 255, 255))
        fond.paste(rgba, mask=rgba.getchannel("A"))
        return fond
    return image.convert("RGB")


# ---------------------------------------------------------------------------
# 1. Créer un PDF
# ---------------------------------------------------------------------------

def creer_pdf(images, destination: Path, progression, arret) -> dict:
    """Assemble les images (dans l'ordre donné) en un seul PDF, une image par page."""
    total = len(images)
    if total == 0:
        raise ErreurConversion("Aucune image à mettre dans le PDF.")

    # On écrit d'abord dans un fichier temporaire : si quelque chose se passe
    # mal, aucun PDF à moitié fini ne traîne dans le dossier de l'utilisateur.
    descripteur, nom_temporaire = tempfile.mkstemp(suffix=".pdf")
    os.close(descripteur)
    temporaire = Path(nom_temporaire)

    erreurs = []   # images illisibles, ignorées
    pages = 0      # pages réellement ajoutées
    try:
        for numero, chemin in enumerate(images):
            _verifier_arret(arret)
            progression(int(numero * 95 / total), f"Image {numero + 1} sur {total}…")

            try:
                page = en_rgb(ouvrir_image(chemin))
            except ErreurConversion as erreur:
                # Une image abîmée ne doit pas empêcher de faire le PDF : on la saute
                erreurs.append(str(erreur))
                continue
            if max(page.size) > COTE_MAX_PDF:
                page.thumbnail((COTE_MAX_PDF, COTE_MAX_PDF), Image.Resampling.LANCZOS)

            # Résolution choisie pour que chaque page ait à peu près la taille d'une A4
            resolution = max(72.0, max(page.size) / POUCES_A4)
            page.save(
                temporaire,
                "PDF",
                resolution=resolution,
                append=pages > 0,  # la 1re image crée le PDF, les suivantes s'ajoutent
                quality=92,
                title="Images",
                creator="Convertisseur",
            )
            page.close()
            pages += 1

        if pages == 0:
            raise ErreurConversion("Aucune image n'a pu être lue.\n\n" + "\n".join(erreurs[:3]))
        _verifier_arret(arret)
        progression(98, "Enregistrement…")
        destination = chemin_unique(Path(destination))
        try:
            shutil.move(str(temporaire), str(destination))
        except PermissionError:
            raise ErreurConversion(
                f"Impossible d'enregistrer le PDF dans « {destination.parent} » : accès refusé."
            )
        except OSError as erreur:
            raise ErreurConversion(f"Impossible d'enregistrer le PDF ({erreur.strerror or erreur}).")
    finally:
        temporaire.unlink(missing_ok=True)

    progression(100, "Terminé")
    return {
        "fichier": destination,
        "pages": pages,
        "taille": destination.stat().st_size,
        "erreurs": erreurs,
    }


# ---------------------------------------------------------------------------
# 2. Réduire la taille des photos
# ---------------------------------------------------------------------------

def reduire_images(images, qualite: int, taille_max: int | None, progression, arret) -> dict:
    """Crée des copies allégées dans un dossier « reduites » à côté des originaux.

    qualite    : de 1 à 100 (75 par défaut)
    taille_max : plus grand côté en pixels (1920, 1280) ou None pour « Originale »
    """
    total = len(images)
    avant = apres = reussies = 0
    erreurs = []
    dossiers = []

    for numero, chemin in enumerate(images):
        _verifier_arret(arret)
        chemin = Path(chemin)
        progression(int(numero * 100 / total), f"Photo {numero + 1} sur {total}…")

        destination = None
        try:
            image = ouvrir_image(chemin)
            if taille_max and max(image.size) > taille_max:
                image.thumbnail((taille_max, taille_max), Image.Resampling.LANCZOS)

            # Choix du format de la copie
            options = {}
            exif = image.getexif()
            profil_couleurs = image.info.get("icc_profile")
            if chemin.suffix.lower() == ".webp":
                format_, extension = "WEBP", ".webp"
                image = image.convert("RGBA" if a_de_la_transparence(image) else "RGB")
                options = {"quality": qualite, "method": 6}
            elif chemin.suffix.lower() == ".png" and a_de_la_transparence(image):
                # PNG transparent : on garde le PNG (le JPG ne sait pas faire la transparence)
                format_, extension = "PNG", ".png"
                image = image.convert("RGBA")
                options = {"optimize": True}
            else:
                # Tout le reste (JPG, HEIC, PNG sans transparence) devient un JPG
                format_, extension = "JPEG", ".jpg"
                image = en_rgb(image)
                options = {"quality": qualite, "optimize": True, "progressive": True}

            if format_ in ("JPEG", "WEBP"):
                if exif:
                    options["exif"] = exif  # garde la date de prise de vue, etc.
                if profil_couleurs:
                    options["icc_profile"] = profil_couleurs

            dossier = chemin.parent / "reduites"
            dossier.mkdir(exist_ok=True)
            destination = chemin_unique(dossier / f"{chemin.stem}{extension}")

            # Ceinture et bretelles : on ne doit jamais écrire sur l'original
            if destination.resolve() == chemin.resolve():
                raise ErreurConversion(f"« {chemin.name} » : enregistrement impossible.")

            try:
                image.save(destination, format_, **options)
            except Exception:
                # Si les métadonnées posent problème, on réessaie sans elles
                options.pop("exif", None)
                options.pop("icc_profile", None)
                image.save(destination, format_, **options)

            avant += chemin.stat().st_size
            apres += destination.stat().st_size
            reussies += 1
            if dossier not in dossiers:
                dossiers.append(dossier)

        except ErreurConversion as erreur:
            erreurs.append(str(erreur))
        except PermissionError:
            erreurs.append(f"« {chemin.name} » : impossible d'écrire dans le dossier (accès refusé).")
        except Exception as erreur:
            journal.exception("Réduction impossible : %s", chemin)
            erreurs.append(f"« {chemin.name} » : {erreur}")
            # On supprime une éventuelle copie à moitié écrite (jamais l'original !)
            if destination is not None and destination != chemin and destination.exists():
                destination.unlink(missing_ok=True)

    if reussies == 0:
        detail = "\n".join(erreurs[:3])
        raise ErreurConversion(f"Aucune photo n'a pu être réduite.\n\n{detail}")

    progression(100, "Terminé")
    return {
        "nombre": reussies,
        "avant": avant,
        "apres": apres,
        "erreurs": erreurs,
        "dossiers": dossiers,
    }


# ---------------------------------------------------------------------------
# 3. Convertir une vidéo en GIF (avec FFmpeg, fourni par imageio-ffmpeg)
# ---------------------------------------------------------------------------

def chemin_ffmpeg() -> str:
    """Emplacement du programme FFmpeg installé automatiquement par pip."""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        journal.exception("FFmpeg introuvable")
        raise ErreurConversion(
            "Le module vidéo (FFmpeg) est introuvable. Réinstalle l'application."
        )


def infos_video(chemin: Path) -> dict:
    """Lit rapidement la durée (en secondes) et la largeur (en pixels) d'une vidéo.

    Renvoie {"duree": float | None, "largeur": int | None}.
    """
    commande = [chemin_ffmpeg(), "-hide_banner", "-nostdin", "-i", str(chemin)]
    try:
        resultat = subprocess.run(
            commande,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=20,
            creationflags=SANS_CONSOLE,
        )
    except subprocess.TimeoutExpired:
        return {"duree": None, "largeur": None}
    texte = resultat.stderr.decode("utf-8", errors="replace")

    duree = None
    trouve = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", texte)
    if trouve:
        h, m, s = trouve.groups()
        duree = int(h) * 3600 + int(m) * 60 + float(s)

    largeur = None
    trouve = re.search(r"Video:.*?\b(\d{2,5})x(\d{2,5})\b", texte)
    if trouve:
        largeur = int(trouve.group(1))

    if duree is None and "Video:" not in texte:
        raise ErreurConversion(
            f"Impossible de lire la vidéo « {Path(chemin).name} ». Elle est peut-être abîmée."
        )
    return {"duree": duree, "largeur": largeur}


def _executer_ffmpeg(commande, duree, debut_pct, fin_pct, texte, progression, arret):
    """Lance FFmpeg et suit son avancement, sans jamais bloquer l'interface.

    FFmpeg écrit régulièrement « out_time_us=… » : on le transforme en pourcentage.
    """
    with tempfile.TemporaryFile() as erreurs:
        processus = subprocess.Popen(
            commande,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=erreurs,
            creationflags=SANS_CONSOLE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            for ligne in processus.stdout:
                if arret():
                    processus.kill()
                    processus.wait()
                    raise ConversionAnnulee()
                cle, _, valeur = ligne.strip().partition("=")
                if cle in ("out_time_us", "out_time_ms") and valeur.isdigit() and duree > 0:
                    fraction = min(1.0, int(valeur) / 1_000_000 / duree)
                    if fin_pct > debut_pct:
                        progression(int(debut_pct + fraction * (fin_pct - debut_pct)), texte)
            code = processus.wait()
        finally:
            if processus.poll() is None:
                processus.kill()
                processus.wait()

        if code != 0:
            erreurs.seek(0)
            detail = erreurs.read().decode("utf-8", errors="replace").strip()
            journal.error("FFmpeg a échoué (%s) : %s", code, detail[-2000:])
            if "No such file" in detail:
                raise ErreurConversion("La vidéo est introuvable. A-t-elle été déplacée ?")
            if "Invalid data" in detail or "moov atom not found" in detail:
                raise ErreurConversion("La vidéo semble abîmée ou n'est pas lisible.")
            if "Permission denied" in detail:
                raise ErreurConversion("Accès refusé : impossible de lire la vidéo ou d'écrire le GIF.")
            raise ErreurConversion("La vidéo n'a pas pu être convertie en GIF.")


def convertir_gif(video: Path, debut: float, fin: float, largeur: int, ips: int,
                  progression, arret) -> dict:
    """Transforme un extrait de la vidéo (de « debut » à « fin », en secondes) en GIF.

    On procède en deux passes pour un GIF de bonne qualité :
        1. FFmpeg analyse l'extrait et choisit les 256 meilleures couleurs (palette) ;
        2. il fabrique le GIF avec cette palette.
    """
    video = Path(video)
    duree = fin - debut
    if duree <= 0:
        raise ErreurConversion("La fin de l'extrait doit être après le début.")

    ffmpeg = chemin_ffmpeg()
    # Redimensionne à la largeur voulue (sans jamais agrandir), en gardant les proportions
    filtres = f"fps={ips},scale=w=min({largeur}\\,iw):h=-1:flags=lanczos"
    extrait = ["-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", str(video)]
    suivi = ["-progress", "pipe:1", "-nostats"]
    base = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y"]

    with tempfile.TemporaryDirectory() as dossier_temporaire:
        palette = Path(dossier_temporaire) / "palette.png"
        gif_temporaire = Path(dossier_temporaire) / "resultat.gif"

        # Passe 1 : la palette de couleurs (durée inconnue -> barre « en attente »)
        progression(-1, "Analyse des couleurs…")
        _executer_ffmpeg(
            base + extrait + ["-vf", f"{filtres},palettegen=stats_mode=diff",
                              "-frames:v", "1"] + suivi + [str(palette)],
            duree, 0, 0, "Analyse des couleurs…", progression, arret,
        )
        if not palette.exists():
            raise ErreurConversion(
                "Aucune image n'a pu être extraite. Vérifie le début et la fin de l'extrait."
            )

        # Passe 2 : le GIF lui-même
        _verifier_arret(arret)
        progression(0, "Création du GIF…")
        _executer_ffmpeg(
            base + extrait + ["-i", str(palette), "-lavfi",
                              f"{filtres}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle",
                              "-loop", "0"] + suivi + ["-f", "gif", str(gif_temporaire)],
            duree, 0, 99, "Création du GIF…", progression, arret,
        )
        if not gif_temporaire.exists() or gif_temporaire.stat().st_size == 0:
            raise ErreurConversion(
                "Le GIF est vide. Vérifie que le début de l'extrait est avant la fin de la vidéo."
            )

        destination = chemin_unique(video.with_suffix(".gif"))
        try:
            shutil.move(str(gif_temporaire), str(destination))
        except PermissionError:
            raise ErreurConversion(
                f"Impossible d'enregistrer le GIF dans « {destination.parent} » : accès refusé."
            )

    progression(100, "Terminé")
    return {
        "fichier": destination,
        "taille": destination.stat().st_size,
        "duree": duree,
        "largeur": largeur,
        "ips": ips,
    }

