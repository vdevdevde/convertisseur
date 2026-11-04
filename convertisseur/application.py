"""Démarrage de l'application : thème, gestion des erreurs, fenêtre."""

import logging
import os
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import QLocale, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from . import NOM_APPLICATION
from .fichiers import chemin_ressource
from .style import appliquer_theme


def _preparer_journal():
    """Note les erreurs dans un petit fichier, utile pour comprendre un problème.

    Emplacement : %LOCALAPPDATA%\\Convertisseur\\journal.txt
    """
    dossier = Path(os.environ.get("LOCALAPPDATA", Path.home())) / NOM_APPLICATION
    try:
        dossier.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=dossier / "journal.txt",
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s %(name)s : %(message)s",
            encoding="utf-8",
        )
    except OSError:
        pass  # pas de journal : ce n'est pas grave


def _erreur_inattendue(type_erreur, valeur, trace):
    """Filet de sécurité : toute erreur imprévue affiche un message au lieu de planter."""
    logging.error("Erreur inattendue :\n%s", "".join(traceback.format_exception(type_erreur, valeur, trace)))
    QMessageBox.warning(
        None, NOM_APPLICATION,
        "Une erreur inattendue est survenue, mais l'application continue de fonctionner.\n\n"
        f"Détail technique : {valeur}",
    )


def demarrer() -> int:
    _preparer_journal()

    # Pour que Windows affiche notre icône dans la barre des tâches
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Convertisseur.App")
        except Exception:
            pass

    application = QApplication(sys.argv)
    application.setApplicationName(NOM_APPLICATION)
    application.setStyle("Fusion")  # style sobre, que l'on peut colorer en noir et blanc
    application.setFont(QFont("Segoe UI", 10))
    # Nombres à la française (virgule décimale)
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
    icone = chemin_ressource("icone.ico")
    if icone.exists():
        application.setWindowIcon(QIcon(str(icone)))

    sys.excepthook = _erreur_inattendue

    # Import ici : le thème et la langue doivent être prêts avant de créer la fenêtre
    from .fenetre import FenetrePrincipale

    fenetre = FenetrePrincipale()

    def suivre_windows(*_):
        fenetre.mettre_a_jour_theme(appliquer_theme(application))

    suivre_windows()
    application.styleHints().colorSchemeChanged.connect(suivre_windows)

    fenetre.show()

    # Fichiers donnés au lancement (ex. : fichiers glissés sur l'icône du .exe)
    fichiers = [a for a in sys.argv[1:] if os.path.exists(a)]
    if fichiers:
        QTimer.singleShot(0, lambda: fenetre.recevoir_fichiers(fichiers))

    return application.exec()
