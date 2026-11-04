"""Éléments d'interface sur mesure : la zone de dépôt et les boutons d'action."""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .style import CLAIR


class ZoneDepot(QWidget):
    """La grande zone « Dépose tes fichiers ici ».

    Bordure fine en pointillés gris ; quand on la survole avec un fichier,
    la bordure devient pleine et noire (blanche en mode sombre).
    Un clic n'importe où dans la zone ouvre aussi la fenêtre « parcourir ».
    """

    parcourir = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._survol = False
        self._couleurs = CLAIR
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(260)

        titre = QLabel("Dépose tes fichiers ici")
        titre.setObjectName("titreZone")
        formats = QLabel("Images JPG, PNG, WEBP, HEIC  ·  Vidéos MP4, MOV, AVI")
        formats.setObjectName("discret")
        lien = QPushButton("ou parcourir")
        lien.setObjectName("lien")
        lien.setCursor(Qt.CursorShape.PointingHandCursor)
        lien.clicked.connect(self.parcourir.emit)

        disposition = QVBoxLayout(self)
        disposition.addStretch(1)
        for element in (titre, formats, lien):
            disposition.addWidget(element, 0, Qt.AlignmentFlag.AlignHCenter)
        disposition.insertSpacing(2, 6)
        disposition.addStretch(1)

    def definir_survol(self, actif: bool):
        self._survol = actif
        self.update()

    def definir_couleurs(self, couleurs: dict):
        self._couleurs = couleurs
        self.update()

    def mouseReleaseEvent(self, evenement):
        if evenement.button() == Qt.MouseButton.LeftButton:
            self.parcourir.emit()

    def paintEvent(self, evenement):
        peintre = QPainter(self)
        peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
        rectangle = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        if self._survol:
            peintre.setBrush(QColor(self._couleurs["survol"]))
            stylo = QPen(QColor(self._couleurs["texte"]), 1.5, Qt.PenStyle.SolidLine)
        else:
            peintre.setBrush(Qt.BrushStyle.NoBrush)
            stylo = QPen(QColor(self._couleurs["trait"]), 1.5, Qt.PenStyle.CustomDashLine)
            stylo.setDashPattern([4, 4])
        peintre.setPen(stylo)
        peintre.drawRoundedRect(rectangle, 12, 12)


class BoutonAction(QPushButton):
    """Un grand bouton avec un titre et une petite description en dessous."""

    def __init__(self, titre: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("action")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(70)
        self.setMinimumWidth(380)

        etiquette_titre = QLabel(titre)
        etiquette_titre.setObjectName("actionTitre")
        etiquette_description = QLabel(description)
        etiquette_description.setObjectName("discret")

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(22, 12, 22, 12)
        disposition.setSpacing(2)
        for etiquette in (etiquette_titre, etiquette_description):
            # Les clics « traversent » le texte et arrivent au bouton
            etiquette.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            disposition.addWidget(etiquette)


def bouton(texte: str, nom: str | None = None) -> QPushButton:
    """Crée un bouton simple. nom = "primaire" (noir plein) ou "lien" (texte souligné)."""
    b = QPushButton(texte)
    if nom:
        b.setObjectName(nom)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b


def etiquette(texte: str = "", nom: str | None = None, retour_ligne: bool = False) -> QLabel:
    """Crée un texte. nom = "titre", "discret", "resume"…"""
    e = QLabel(texte)
    if nom:
        e.setObjectName(nom)
    e.setWordWrap(retour_ligne)
    return e
