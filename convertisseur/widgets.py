"""Éléments d'interface sur mesure, style « terminal » :
l'en-tête « convertisseur_ », les cartes d'action sur lesquelles on dépose
les fichiers, et de petites fonctions pour créer boutons et textes."""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .style import CLAIR


# ---------------------------------------------------------------------------
# Petites fonctions pratiques
# ---------------------------------------------------------------------------

def bouton(texte: str, nom: str | None = None) -> QPushButton:
    """Crée un bouton. nom = "primaire" (plein) ou "lien" (texte façon [lien])."""
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


# ---------------------------------------------------------------------------
# En-tête : « convertisseur_ » avec un curseur qui clignote, et la version
# ---------------------------------------------------------------------------

class EnTete(QWidget):
    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        nom = etiquette("convertisseur", "logo")
        self._curseur = etiquette("_", "logo")
        self._curseur.setFixedWidth(self._curseur.sizeHint().width() + 2)
        version = etiquette(f"v{version}", "discret")

        ligne = QHBoxLayout(self)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(0)
        ligne.addWidget(nom)
        ligne.addWidget(self._curseur)
        ligne.addStretch(1)
        ligne.addWidget(version)

        # Le « _ » clignote comme le curseur d'un terminal
        self._visible = True
        minuteur = QTimer(self, interval=550)
        minuteur.timeout.connect(self._clignoter)
        minuteur.start()

    def _clignoter(self):
        self._visible = not self._visible
        self._curseur.setText("_" if self._visible else " ")


# ---------------------------------------------------------------------------
# Icônes dessinées au trait (pas de fichier image à fournir)
# ---------------------------------------------------------------------------

class Icone(QWidget):
    """Petite icône au trait : "document", "reduire" ou "lecture"."""

    def __init__(self, forme: str, parent=None):
        super().__init__(parent)
        self._forme = forme
        self._couleur = QColor(CLAIR["texte"])
        self.setFixedSize(28, 28)

    def definir_couleur(self, couleur: str):
        self._couleur = QColor(couleur)
        self.update()

    def paintEvent(self, evenement):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        stylo = QPen(self._couleur, 1.6)
        stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
        stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(stylo)
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._forme == "document":
            # Feuille avec un coin plié et deux lignes de texte
            chemin = QPainterPath(QPointF(6, 3))
            chemin.lineTo(17, 3)
            chemin.lineTo(22, 8)
            chemin.lineTo(22, 25)
            chemin.lineTo(6, 25)
            chemin.closeSubpath()
            p.drawPath(chemin)
            p.drawPolyline([QPointF(17, 3), QPointF(17, 8), QPointF(22, 8)])
            p.drawLine(QPointF(10, 14), QPointF(18, 14))
            p.drawLine(QPointF(10, 18), QPointF(16, 18))
        elif self._forme == "reduire":
            # Deux flèches qui se rejoignent vers le centre
            p.drawLine(QPointF(4, 24), QPointF(12, 16))
            p.drawPolyline([QPointF(6, 16), QPointF(12, 16), QPointF(12, 22)])
            p.drawLine(QPointF(24, 4), QPointF(16, 12))
            p.drawPolyline([QPointF(16, 6), QPointF(16, 12), QPointF(22, 12)])
        else:
            # Écran avec un bouton « lecture »
            p.drawRoundedRect(QRectF(3, 5, 22, 18), 3, 3)
            triangle = QPainterPath(QPointF(12, 10))
            triangle.lineTo(18, 14)
            triangle.lineTo(12, 18)
            triangle.closeSubpath()
            p.drawPath(triangle)


# ---------------------------------------------------------------------------
# Carte d'action : on dépose les fichiers directement dessus
# ---------------------------------------------------------------------------

class CarteAction(QWidget):
    """Une des trois grandes cartes de l'accueil.

    - Bordure fine en pointillés au repos ;
    - bordure pleine quand on la survole avec des fichiers compatibles
      (« relâche pour convertir ») ;
    - estompée avec « incompatible » si les fichiers ne lui conviennent pas.
    Un clic ouvre la fenêtre « parcourir » pour cette action.
    """

    fichiers_deposes = Signal(list)  # chemins déposés sur la carte
    cliquee = Signal()

    def __init__(self, numero: str, forme: str, titre: str, description: str,
                 formats: str, extensions: set, parent=None):
        super().__init__(parent)
        self.extensions = extensions
        self._formats = formats
        self._etat = "repos"   # repos, survol, depot, refus, attente, inactif
        self._couleurs = CLAIR
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(180, 300)

        self._numero = etiquette(numero, "discret")
        self._icone = Icone(forme)
        self._titre = etiquette(titre, "titreCarte")
        self._description = etiquette(description, "discret", retour_ligne=True)
        self._pied = etiquette(formats, "pied")

        disposition = QVBoxLayout(self)
        disposition.setContentsMargins(22, 20, 22, 20)
        disposition.setSpacing(0)
        disposition.addWidget(self._numero)
        disposition.addSpacing(14)
        disposition.addWidget(self._icone)
        disposition.addStretch(1)
        disposition.addWidget(self._titre)
        disposition.addSpacing(8)
        disposition.addWidget(self._description)
        disposition.addSpacing(16)
        disposition.addWidget(self._pied)

    # --- Apparence ---

    def definir_couleurs(self, couleurs: dict):
        self._couleurs = couleurs
        self._appliquer_etat()

    def definir_etat(self, etat: str):
        """etat = "repos", "attente" (fichiers prêts, carte compatible) ou "inactif"."""
        self._etat = etat
        self._appliquer_etat()

    def _appliquer_etat(self):
        c = self._couleurs
        textes = {
            "depot": "relâche pour convertir",
            "refus": "incompatible",
            "attente": "clique pour continuer",
            "inactif": "incompatible",
        }
        self._pied.setText(textes.get(self._etat, self._formats))
        actif = self._etat in ("depot", "attente")
        estompe = self._etat in ("refus", "inactif")
        self._pied.setStyleSheet(f"color: {c['texte'] if actif else c['doux']};")
        self._titre.setStyleSheet(f"color: {c['doux'] if estompe else c['texte']};")
        self._icone.definir_couleur(c["doux"] if estompe else c["texte"])
        self.update()

    def paintEvent(self, evenement):
        c = self._couleurs
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rectangle = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        if self._etat in ("depot", "attente"):
            p.setBrush(QColor(c["carte"]))
            stylo = QPen(QColor(c["texte"]), 1)
        elif self._etat == "survol":
            p.setBrush(QColor(c["carte"]))
            stylo = QPen(QColor(c["doux"]), 1)
        else:
            p.setBrush(Qt.BrushStyle.NoBrush)
            stylo = QPen(QColor(c["trait"]), 1, Qt.PenStyle.CustomDashLine)
            stylo.setDashPattern([3, 3])
        p.setPen(stylo)
        p.drawRoundedRect(rectangle, 3, 3)

    # --- Souris ---

    def enterEvent(self, evenement):
        if self._etat == "repos":
            self._etat = "survol"
            self._appliquer_etat()

    def leaveEvent(self, evenement):
        if self._etat == "survol":
            self._etat = "repos"
            self._appliquer_etat()

    def mouseReleaseEvent(self, evenement):
        if evenement.button() == Qt.MouseButton.LeftButton and self.rect().contains(
                evenement.position().toPoint()):
            self.cliquee.emit()

    # --- Glisser-déposer ---

    def accepte(self, chemins) -> bool:
        """Vrai si au moins un des fichiers convient à cette carte (un dossier : on essaie)."""
        for chemin in chemins:
            chemin = Path(chemin)
            if chemin.suffix.lower() in self.extensions or chemin.is_dir():
                return True
        return False

    @staticmethod
    def _chemins(evenement):
        donnees = evenement.mimeData()
        if not donnees.hasUrls():
            return []
        return [u.toLocalFile() for u in donnees.urls() if u.isLocalFile()]

    def dragEnterEvent(self, evenement):
        chemins = self._chemins(evenement)
        if not chemins:
            evenement.ignore()
            return
        self._etat_avant = self._etat
        if self.accepte(chemins):
            self._etat = "depot"
            evenement.acceptProposedAction()
        else:
            # On accepte quand même l'entrée pour afficher « incompatible »,
            # mais le dépôt sera refusé (curseur « interdit »)
            self._etat = "refus"
            evenement.accept()
        self._appliquer_etat()

    def dragMoveEvent(self, evenement):
        if self._etat == "depot":
            evenement.acceptProposedAction()
        else:
            evenement.ignore()

    def dragLeaveEvent(self, evenement):
        self._etat = getattr(self, "_etat_avant", "repos")
        if self._etat == "survol":
            self._etat = "repos"
        self._appliquer_etat()

    def dropEvent(self, evenement):
        chemins = self._chemins(evenement)
        self._etat = "repos"
        self._appliquer_etat()
        if chemins and self.accepte(chemins):
            evenement.acceptProposedAction()
            self.fichiers_deposes.emit(chemins)
