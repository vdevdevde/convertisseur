"""Exécution des conversions en arrière-plan.

Une conversion peut durer plusieurs secondes. Si on la lançait directement,
la fenêtre serait « figée » pendant ce temps. On la lance donc dans un
fil d'exécution séparé (QThread) qui envoie des signaux à la fenêtre :
progression, réussite, échec ou annulation.
"""

import logging
import traceback
from pathlib import Path

from PIL import Image, ImageOps
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from .conversions import ConversionAnnulee, ErreurConversion  # active aussi le HEIC

journal = logging.getLogger(__name__)


class Tache(QThread):
    """Lance une fonction de conversions.py en arrière-plan."""

    progression = Signal(int, str)   # pourcentage (-1 = inconnu), texte
    reussite = Signal(object)        # le résultat renvoyé par la fonction
    echec = Signal(str)              # message d'erreur en français
    annulee = Signal()

    def __init__(self, fonction, parametres: dict, parent=None):
        super().__init__(parent)
        self._fonction = fonction
        self._parametres = parametres
        self._arret_demande = False

    def annuler(self):
        """Demande poliment à la conversion de s'arrêter dès que possible."""
        self._arret_demande = True

    def run(self):
        try:
            resultat = self._fonction(
                progression=self.progression.emit,
                arret=lambda: self._arret_demande,
                **self._parametres,
            )
        except ConversionAnnulee:
            self.annulee.emit()
        except ErreurConversion as erreur:
            self.echec.emit(str(erreur))
        except MemoryError:
            self.echec.emit(
                "Pas assez de mémoire pour terminer. Essaie avec moins de fichiers à la fois."
            )
        except Exception as erreur:  # filet de sécurité : jamais de plantage
            journal.error("Erreur inattendue :\n%s", traceback.format_exc())
            self.echec.emit(f"Une erreur inattendue est survenue.\n\nDétail technique : {erreur}")
        else:
            self.reussite.emit(resultat)


class ChargeurMiniatures(QThread):
    """Prépare les petites vignettes des images, une par une, en arrière-plan."""

    miniature = Signal(str, QImage)  # chemin de l'image, vignette

    def __init__(self, chemins, taille: int, parent=None):
        super().__init__(parent)
        self._chemins = [Path(c) for c in chemins]
        self._taille = taille
        self._arret_demande = False

    def arreter(self):
        self._arret_demande = True

    def run(self):
        for chemin in self._chemins:
            if self._arret_demande:
                return
            try:
                with Image.open(chemin) as source:
                    # draft() accélère beaucoup la lecture des gros JPG
                    source.draft("RGB", (self._taille * 2, self._taille * 2))
                    image = ImageOps.exif_transpose(source)
                    image.thumbnail((self._taille, self._taille), Image.Resampling.LANCZOS)
                    image = image.convert("RGBA")
                donnees = image.tobytes("raw", "RGBA")
                vignette = QImage(
                    donnees, image.width, image.height, image.width * 4,
                    QImage.Format.Format_RGBA8888,
                ).copy()  # copy() : la QImage garde ses propres données
                self.miniature.emit(str(chemin), vignette)
            except Exception:
                # Pas grave : la case grise reste affichée à la place de la vignette
                journal.warning("Vignette impossible pour %s", chemin)
