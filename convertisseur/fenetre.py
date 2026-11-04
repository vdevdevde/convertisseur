"""La fenêtre principale de Convertisseur (style « terminal »).

En haut, toujours visible : l'en-tête « convertisseur_ » et la version.
En dessous, plusieurs « écrans » empilés (un seul visible à la fois) :
    accueil   -> trois cartes : on dépose les fichiers directement sur l'action voulue
    pdf       -> les miniatures à réordonner, puis « créer le pdf »
    reduire   -> qualité + taille maximale, puis « réduire »
    gif       -> début, fin, largeur, images par seconde, puis « créer le gif »
    travail   -> la barre de progression pendant la conversion
    resultat  -> le résultat, avec « ouvrir le dossier » et « recommencer »
"""

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QComboBox, QDoubleSpinBox, QFileDialog,
    QFrame, QGridLayout, QHBoxLayout, QListView, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QProgressBar, QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from . import DEPOT_GITHUB, NOM_APPLICATION, VERSION, mise_a_jour
from .conversions import ErreurConversion, convertir_gif, creer_pdf, infos_video, reduire_images
from .fichiers import (
    EXTENSIONS_IMAGES, EXTENSIONS_VIDEOS, chemin_ressource, duree_lisible, nombre,
    ouvrir_dans_explorateur, taille_lisible, trier_fichiers,
)
from .style import CLAIR
from .taches import ChargeurMiniatures, Tache
from .widgets import CarteAction, EnTete, bouton, etiquette

TAILLE_MINIATURE = 120
MARGE = 36  # marge sur les côtés de la fenêtre

TEXTE_ATTENTE = "> en attente de fichiers…"


class RelaisMiseAJour(QObject):
    """Fait passer les nouvelles de la mise à jour (fil d'arrière-plan) vers la fenêtre."""

    trouvee = Signal(object)       # infos sur la nouvelle version
    progression = Signal(int, str)
    prete = Signal(object)         # la nouvelle version est téléchargée et décompressée
    echec = Signal(str)


class FenetrePrincipale(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(NOM_APPLICATION)
        icone = chemin_ressource("icone.ico")
        if icone.exists():
            self.setWindowIcon(QIcon(str(icone)))
        self.resize(820, 620)
        self.setMinimumSize(700, 560)

        # État : les fichiers en cours de traitement
        self.images: list[Path] = []
        self.videos: list[Path] = []
        self.en_attente: list[Path] = []   # fichiers choisis avec [parcourir], pas encore utilisés
        self.tache: Tache | None = None
        self.chargeur: ChargeurMiniatures | None = None
        self.infos_gif: dict = {}
        self.couleurs = CLAIR
        self._a_ouvrir: Path | None = None   # ce que « ouvrir le dossier » montrera
        self._page_retour: QWidget | None = None

        # En-tête + écrans + bandeau de mise à jour
        self.pile = QStackedWidget()
        self.bandeau_maj = self._construire_bandeau_maj()
        centre = QWidget()
        disposition_centre = QVBoxLayout(centre)
        disposition_centre.setContentsMargins(0, 0, 0, 0)
        disposition_centre.setSpacing(0)
        en_tete = EnTete(VERSION)
        en_tete.setContentsMargins(MARGE, 24, MARGE, 0)
        disposition_centre.addWidget(en_tete)
        disposition_centre.addWidget(self.pile, 1)
        disposition_centre.addWidget(self.bandeau_maj)
        self.setCentralWidget(centre)

        self.page_accueil = self._construire_accueil()
        self.page_pdf = self._construire_pdf()
        self.page_reduire = self._construire_reduire()
        self.page_gif = self._construire_gif()
        self.page_travail = self._construire_travail()
        self.page_resultat = self._construire_resultat()
        for page in (self.page_accueil, self.page_pdf, self.page_reduire,
                     self.page_gif, self.page_travail, self.page_resultat):
            self.pile.addWidget(page)

        # Petit minuteur pour remettre la ligne d'état à zéro après quelques secondes
        self._minuteur_message = QTimer(self, singleShot=True, interval=6000)
        self._minuteur_message.timeout.connect(self._etat_par_defaut)

        # Recherche discrète d'une nouvelle version, peu après l'ouverture
        if not DEPOT_GITHUB.startswith("PROPRIETAIRE"):
            QTimer.singleShot(1500, self._verifier_mise_a_jour)

    # ------------------------------------------------------------------
    # Outils de mise en page
    # ------------------------------------------------------------------

    @staticmethod
    def _nouvelle_page():
        """Crée un écran vide avec de belles marges."""
        page = QWidget()
        disposition = QVBoxLayout(page)
        disposition.setContentsMargins(MARGE, 28, MARGE, 28)
        disposition.setSpacing(0)
        return page, disposition

    @staticmethod
    def _barre_du_bas(*elements):
        """Ligne de boutons en bas d'écran. None = espace extensible."""
        ligne = QHBoxLayout()
        ligne.setSpacing(10)
        for element in elements:
            if element is None:
                ligne.addStretch(1)
            else:
                ligne.addWidget(element)
        return ligne

    @staticmethod
    def _ligne():
        """Fine ligne horizontale de séparation."""
        trait = QFrame()
        trait.setObjectName("ligne")
        return trait

    def mettre_a_jour_theme(self, couleurs: dict):
        """Appelé quand Windows passe du mode clair au mode sombre (ou l'inverse)."""
        self.couleurs = couleurs
        for carte in self.cartes:
            carte.definir_couleurs(couleurs)
        # Les cases grises des miniatures pas encore chargées
        for i in range(self.liste_pdf.count()):
            element = self.liste_pdf.item(i)
            if not element.data(Qt.ItemDataRole.UserRole + 1):
                element.setIcon(self._icone_attente())

    # ------------------------------------------------------------------
    # Écran 1 : accueil (les trois cartes d'action)
    # ------------------------------------------------------------------

    def _construire_accueil(self):
        page, disposition = self._nouvelle_page()
        titre = etiquette("que veux-tu faire ?", "titre")
        sous_titre = etiquette("dépose tes fichiers directement sur l'action voulue.", "discret")

        images = "jpg · png · webp · heic"
        self.carte_pdf = CarteAction(
            "01", "document", "images → pdf",
            "plusieurs images deviennent un seul pdf.", images, EXTENSIONS_IMAGES)
        self.carte_reduire = CarteAction(
            "02", "reduire", "réduire photos",
            "allège tes photos sans toucher aux originaux.", images, EXTENSIONS_IMAGES)
        self.carte_gif = CarteAction(
            "03", "lecture", "vidéo → gif",
            "un extrait de vidéo en gif animé.", "mp4 · mov · avi", EXTENSIONS_VIDEOS)
        self.cartes = (self.carte_pdf, self.carte_reduire, self.carte_gif)
        for carte, action in zip(self.cartes, ("pdf", "reduire", "gif")):
            carte.fichiers_deposes.connect(lambda chemins, a=action: self._demarrer(a, chemins))
            carte.cliquee.connect(lambda a=action: self._carte_cliquee(a))

        ligne_cartes = QHBoxLayout()
        ligne_cartes.setSpacing(14)
        for carte in self.cartes:
            ligne_cartes.addWidget(carte, 1)

        # Ligne d'état façon terminal : « > en attente de fichiers… [parcourir] »
        self.etat_accueil = etiquette(TEXTE_ATTENTE, "discret")
        self.lien_parcourir = bouton("[parcourir]", "lien")
        self.lien_parcourir.clicked.connect(self._parcourir)
        self.lien_vider = bouton("[vider]", "lien")
        self.lien_vider.clicked.connect(self._vider_attente)
        self.lien_vider.hide()
        rappel = etiquette("originaux jamais modifiés", "discret")

        ligne_etat = QHBoxLayout()
        ligne_etat.setSpacing(8)
        ligne_etat.addWidget(self.etat_accueil)
        ligne_etat.addWidget(self.lien_parcourir)
        ligne_etat.addWidget(self.lien_vider)
        ligne_etat.addStretch(1)
        ligne_etat.addWidget(rappel)

        disposition.addWidget(titre)
        disposition.addSpacing(6)
        disposition.addWidget(sous_titre)
        disposition.addSpacing(24)
        disposition.addLayout(ligne_cartes, 1)
        disposition.addSpacing(20)
        disposition.addWidget(self._ligne())
        disposition.addSpacing(14)
        disposition.addLayout(ligne_etat)
        return page

    def _afficher_etat(self, texte: str, temporaire: bool = True):
        """Écrit un message dans la ligne d'état de l'accueil."""
        self.etat_accueil.setText(texte)
        if temporaire:
            self._minuteur_message.start()
        else:
            self._minuteur_message.stop()

    def _etat_par_defaut(self):
        if self.en_attente:
            images, videos, _ = trier_fichiers(self.en_attente)
            morceaux = []
            if images:
                morceaux.append(nombre(len(images), "image"))
            if videos:
                morceaux.append(nombre(len(videos), "vidéo"))
            # Accord : « 2 images prêtes », « 1 vidéo prête », « 2 images · 1 vidéo prêtes »
            pret = "prêtes" if len(images) + len(videos) > 1 else "prête"
            self._afficher_etat(f"> {' · '.join(morceaux)} {pret} — clique sur une action",
                                temporaire=False)
        else:
            self._afficher_etat(TEXTE_ATTENTE, temporaire=False)

    def _parcourir(self):
        """[parcourir] : on choisit des fichiers, puis on clique sur une action."""
        motifs = " ".join(f"*{e}" for e in sorted(EXTENSIONS_IMAGES | EXTENSIONS_VIDEOS))
        chemins, _ = QFileDialog.getOpenFileNames(
            self, "Choisir des fichiers", str(Path.home()),
            f"Images et vidéos ({motifs});;Tous les fichiers (*)",
        )
        if chemins:
            self.recevoir_fichiers(chemins)

    def _vider_attente(self):
        self.en_attente = []
        for carte in self.cartes:
            carte.definir_etat("repos")
        self.lien_vider.hide()
        self.lien_parcourir.show()
        self._etat_par_defaut()

    def _carte_cliquee(self, action: str):
        """Clic sur une carte : on utilise les fichiers en attente, sinon on parcourt."""
        carte = {"pdf": self.carte_pdf, "reduire": self.carte_reduire, "gif": self.carte_gif}[action]
        if self.en_attente:
            if carte.accepte(self.en_attente):
                self._demarrer(action, self.en_attente)
            else:
                self._afficher_etat("> incompatible avec cette action")
            return
        extensions = " ".join(f"*{e}" for e in sorted(carte.extensions))
        genre = "Vidéos" if action == "gif" else "Images"
        chemins, _ = QFileDialog.getOpenFileNames(
            self, "Choisir des fichiers", str(Path.home()), f"{genre} ({extensions})")
        if chemins:
            self._demarrer(action, chemins)

    def _demarrer(self, action: str, chemins):
        """Fichiers reçus pour une action : on garde ceux qui conviennent et on y va."""
        images, videos, ignores = trier_fichiers(chemins)
        utiles = videos if action == "gif" else images
        inutiles = len(ignores) + len(images if action == "gif" else videos)
        if not utiles:
            attendu = "une vidéo" if action == "gif" else "des images"
            self._afficher_etat(f"> incompatible : il faut {attendu}")
            return

        self._vider_attente()
        if action == "gif":
            self.videos = videos
            self._ouvrir_gif()
        else:
            self.images = images
            if action == "pdf":
                self._preparer_miniatures()
                self.pile.setCurrentWidget(self.page_pdf)
            else:
                self._ouvrir_reduire()
        # Les fichiers mis de côté sont signalés sur l'écran de l'action
        self.note_ignores = (
            f"{nombre(inutiles, 'fichier ignoré', 'fichiers ignorés')} (type non compatible)"
            if inutiles else "")
        for note in (self.ignores_pdf, self.ignores_reduire, self.ignores_gif):
            note.setText(self.note_ignores)

    # ------------------------------------------------------------------
    # Écran 2 : images → pdf
    # ------------------------------------------------------------------

    def _en_tete_action(self, disposition, numero: str, titre: str, aide: str):
        """Titre commun aux écrans d'action : « 01  images → pdf »."""
        ligne = QHBoxLayout()
        ligne.setSpacing(14)
        ligne.addWidget(etiquette(numero, "discret"), 0, Qt.AlignmentFlag.AlignBottom)
        ligne.addWidget(etiquette(titre, "titre"))
        ligne.addStretch(1)
        disposition.addLayout(ligne)
        disposition.addSpacing(6)
        texte_aide = etiquette(aide, "discret", retour_ligne=True)
        disposition.addWidget(texte_aide)
        return texte_aide

    def _construire_pdf(self):
        page, disposition = self._nouvelle_page()
        self._en_tete_action(disposition, "01", "images → pdf",
                             "une image par page · glisse les miniatures pour changer l'ordre.")

        # Liste de miniatures que l'on peut réordonner en les faisant glisser
        self.liste_pdf = QListWidget()
        self.liste_pdf.setViewMode(QListView.ViewMode.ListMode)
        self.liste_pdf.setFlow(QListView.Flow.LeftToRight)
        self.liste_pdf.setWrapping(True)
        self.liste_pdf.setResizeMode(QListView.ResizeMode.Adjust)
        self.liste_pdf.setIconSize(QSize(TAILLE_MINIATURE, TAILLE_MINIATURE))
        self.liste_pdf.setSpacing(6)
        self.liste_pdf.setUniformItemSizes(True)
        self.liste_pdf.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.liste_pdf.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.liste_pdf.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        self.ignores_pdf = etiquette("", "discret")
        retour = bouton("[retour]", "lien")
        retour.clicked.connect(self.recommencer)
        creer = bouton("créer le pdf →", "primaire")
        creer.clicked.connect(self._lancer_pdf)

        disposition.addSpacing(20)
        disposition.addWidget(self.liste_pdf, 1)
        disposition.addSpacing(8)
        disposition.addWidget(self.ignores_pdf)
        disposition.addSpacing(12)
        disposition.addLayout(self._barre_du_bas(retour, None, creer))
        return page

    def _icone_attente(self) -> QIcon:
        """Case grise affichée tant que la miniature n'est pas prête."""
        image = QPixmap(TAILLE_MINIATURE, TAILLE_MINIATURE)
        image.fill(QColor(self.couleurs["piste"]))
        return QIcon(image)

    def _preparer_miniatures(self):
        """Remplit la liste du PDF et lance la fabrication des vignettes en arrière-plan."""
        self._arreter_miniatures()
        self.liste_pdf.clear()
        self._elements_pdf = {}
        attente = self._icone_attente()
        for chemin in self.images:
            element = QListWidgetItem(attente, "")
            element.setData(Qt.ItemDataRole.UserRole, str(chemin))
            element.setToolTip(chemin.name)
            element.setSizeHint(QSize(TAILLE_MINIATURE + 14, TAILLE_MINIATURE + 14))
            self.liste_pdf.addItem(element)
            self._elements_pdf[str(chemin)] = element

        if self.images:
            self.chargeur = ChargeurMiniatures(self.images, TAILLE_MINIATURE, self)
            self.chargeur.miniature.connect(self._afficher_miniature)
            self.chargeur.start()

    def _afficher_miniature(self, chemin: str, vignette):
        element = self._elements_pdf.get(chemin)
        if element is not None:
            element.setIcon(QIcon(QPixmap.fromImage(vignette)))
            element.setData(Qt.ItemDataRole.UserRole + 1, True)  # « vignette chargée »

    def _arreter_miniatures(self):
        if self.chargeur is not None:
            self.chargeur.arreter()
            self.chargeur.wait(3000)
            self.chargeur = None

    def _lancer_pdf(self):
        # L'ordre des pages = l'ordre actuel des miniatures
        ordre = [Path(self.liste_pdf.item(i).data(Qt.ItemDataRole.UserRole))
                 for i in range(self.liste_pdf.count())]
        if not ordre:
            return
        destination = ordre[0].parent / "images.pdf"
        self._lancer(
            creer_pdf, {"images": ordre, "destination": destination},
            "> création du pdf", self._pdf_termine, self.page_pdf,
        )

    def _pdf_termine(self, resultat: dict):
        detail = str(resultat["fichier"])
        if resultat["erreurs"]:
            detail += ("\n\nimage(s) ignorée(s) car illisible(s) :\n"
                       + "\n".join(resultat["erreurs"][:4]))
        self._afficher_resultat(
            "> pdf créé",
            f"{nombre(resultat['pages'], 'page')} · {taille_lisible(resultat['taille'])}",
            detail,
            resultat["fichier"],
        )

    # ------------------------------------------------------------------
    # Écran 3 : réduire photos
    # ------------------------------------------------------------------

    def _construire_reduire(self):
        page, disposition = self._nouvelle_page()
        self.resume_reduire = self._en_tete_action(disposition, "02", "réduire photos", "")

        # Curseur « qualité »
        self.valeur_qualite = etiquette("75")
        self.curseur_qualite = QSlider(Qt.Orientation.Horizontal)
        self.curseur_qualite.setRange(10, 100)
        self.curseur_qualite.setValue(75)
        self.curseur_qualite.setCursor(Qt.CursorShape.PointingHandCursor)
        self.curseur_qualite.valueChanged.connect(lambda v: self.valeur_qualite.setText(str(v)))
        ligne_qualite = QHBoxLayout()
        ligne_qualite.addWidget(etiquette("qualité", "etiquette"))
        ligne_qualite.addStretch(1)
        ligne_qualite.addWidget(self.valeur_qualite)

        # Choix de la taille maximale
        self.groupe_taille = QButtonGroup(self)
        ligne_taille = QHBoxLayout()
        ligne_taille.setSpacing(8)
        for texte, valeur in (("originale", 0), ("1920 px", 1920), ("1280 px", 1280)):
            b = bouton(texte, "choix")
            b.setCheckable(True)
            self.groupe_taille.addButton(b, valeur)
            ligne_taille.addWidget(b)
        ligne_taille.addStretch(1)
        self.groupe_taille.button(0).setChecked(True)

        note = etiquette(
            "> les copies vont dans un nouveau dossier « reduites » à côté des originaux,\n"
            "  qui ne sont jamais modifiés. heic et png sans transparence deviennent des jpg.",
            "discret", retour_ligne=True)

        self.ignores_reduire = etiquette("", "discret")
        retour = bouton("[retour]", "lien")
        retour.clicked.connect(self.recommencer)
        lancer = bouton("réduire →", "primaire")
        lancer.clicked.connect(self._lancer_reduction)

        disposition.addSpacing(36)
        disposition.addLayout(ligne_qualite)
        disposition.addSpacing(12)
        disposition.addWidget(self.curseur_qualite)
        disposition.addSpacing(8)
        disposition.addWidget(etiquette("plus bas = fichiers plus légers", "discret"))
        disposition.addSpacing(32)
        disposition.addWidget(etiquette("taille maximale", "etiquette"))
        disposition.addSpacing(10)
        disposition.addLayout(ligne_taille)
        disposition.addSpacing(32)
        disposition.addWidget(note)
        disposition.addStretch(1)
        disposition.addWidget(self.ignores_reduire)
        disposition.addSpacing(12)
        disposition.addLayout(self._barre_du_bas(retour, None, lancer))
        return page

    def _ouvrir_reduire(self):
        total = 0
        for chemin in self.images:
            try:
                total += chemin.stat().st_size
            except OSError:
                pass
        self.resume_reduire.setText(f"{nombre(len(self.images), 'photo')} · {taille_lisible(total)}")
        self.pile.setCurrentWidget(self.page_reduire)

    def _lancer_reduction(self):
        taille = self.groupe_taille.checkedId()
        self._lancer(
            reduire_images,
            {"images": list(self.images), "qualite": self.curseur_qualite.value(),
             "taille_max": taille or None},
            "> réduction des photos", self._reduction_terminee, self.page_reduire,
        )

    def _reduction_terminee(self, r: dict):
        resume = (f"{nombre(r['nombre'], 'photo')} · "
                  f"{taille_lisible(r['avant'])} → {taille_lisible(r['apres'])}")
        detail = "enregistrées dans le dossier « reduites »."
        if r["erreurs"]:
            detail += (f"\n\n{nombre(len(r['erreurs']), 'fichier n’a', 'fichiers n’ont')} "
                       "pas pu être traité" + ("s" if len(r["erreurs"]) > 1 else "") + " :\n"
                       + "\n".join(r["erreurs"][:4]))
            if len(r["erreurs"]) > 4:
                detail += "\n…"
        self._afficher_resultat("> photos réduites", resume, detail, r["dossiers"][0])

    # ------------------------------------------------------------------
    # Écran 4 : vidéo → gif
    # ------------------------------------------------------------------

    def _construire_gif(self):
        page, disposition = self._nouvelle_page()
        self.resume_gif = self._en_tete_action(disposition, "03", "vidéo → gif", "")

        self.choix_video = QComboBox()
        self.choix_video.currentIndexChanged.connect(self._video_choisie)

        self.champ_debut = QDoubleSpinBox()
        self.champ_fin = QDoubleSpinBox()
        for champ in (self.champ_debut, self.champ_fin):
            champ.setDecimals(1)
            champ.setSingleStep(0.5)
            champ.setSuffix(" s")
            champ.setRange(0, 36000)
            champ.valueChanged.connect(self._verifier_extrait)

        self.champ_largeur = QSpinBox()
        self.champ_largeur.setRange(80, 1920)
        self.champ_largeur.setSingleStep(20)
        self.champ_largeur.setValue(480)
        self.champ_largeur.setSuffix(" px")

        self.champ_ips = QSpinBox()
        self.champ_ips.setRange(1, 30)
        self.champ_ips.setValue(10)

        grille = QGridLayout()
        grille.setHorizontalSpacing(24)
        grille.setVerticalSpacing(8)
        for colonne, (texte, champ) in enumerate((("début", self.champ_debut),
                                                  ("fin", self.champ_fin))):
            grille.addWidget(etiquette(texte, "etiquette"), 0, colonne)
            grille.addWidget(champ, 1, colonne)
        grille.setRowMinimumHeight(2, 20)
        for colonne, (texte, champ) in enumerate((("largeur", self.champ_largeur),
                                                  ("images/s", self.champ_ips))):
            grille.addWidget(etiquette(texte, "etiquette"), 3, colonne)
            grille.addWidget(champ, 4, colonne)
        grille.setColumnStretch(2, 1)

        self.alerte_gif = etiquette("", "discret", retour_ligne=True)
        astuce = etiquette(
            "> astuce : un extrait court (moins de 10 s) et une petite largeur\n"
            "  donnent un gif plus léger.", "discret", retour_ligne=True)

        self.ignores_gif = etiquette("", "discret")
        retour = bouton("[retour]", "lien")
        retour.clicked.connect(self.recommencer)
        self.bouton_creer_gif = bouton("créer le gif →", "primaire")
        self.bouton_creer_gif.clicked.connect(self._lancer_gif)

        disposition.addSpacing(20)
        disposition.addWidget(self.choix_video)
        disposition.addSpacing(20)
        disposition.addLayout(grille)
        disposition.addSpacing(18)
        disposition.addWidget(self.alerte_gif)
        disposition.addSpacing(16)
        disposition.addWidget(astuce)
        disposition.addStretch(1)
        disposition.addWidget(self.ignores_gif)
        disposition.addSpacing(12)
        disposition.addLayout(self._barre_du_bas(retour, None, self.bouton_creer_gif))
        return page

    def _ouvrir_gif(self):
        # S'il y a plusieurs vidéos, un menu permet de choisir laquelle convertir
        self.choix_video.blockSignals(True)
        self.choix_video.clear()
        for video in self.videos:
            self.choix_video.addItem(video.name)
        self.choix_video.blockSignals(False)
        self.choix_video.setVisible(len(self.videos) > 1)
        self._video_choisie(0)
        self.pile.setCurrentWidget(self.page_gif)

    def _video_choisie(self, index: int):
        if not (0 <= index < len(self.videos)):
            return
        video = self.videos[index]
        try:
            self.infos_gif = infos_video(video)
        except ErreurConversion as erreur:
            self.infos_gif = {"duree": None, "largeur": None}
            self.alerte_gif.setText(str(erreur))
        duree = self.infos_gif.get("duree")

        morceaux = [video.name]
        if duree:
            morceaux.append(duree_lisible(duree))
        if self.infos_gif.get("largeur"):
            morceaux.append(f"{self.infos_gif['largeur']} px de large")
        self.resume_gif.setText(" · ".join(morceaux))

        maximum = round(duree, 1) if duree else 36000
        for champ in (self.champ_debut, self.champ_fin):
            champ.blockSignals(True)
            champ.setMaximum(maximum)
            champ.blockSignals(False)
        self.champ_debut.setValue(0)
        self.champ_fin.setValue(min(maximum, 10.0))
        self._verifier_extrait()

    def _verifier_extrait(self):
        """Désactive « créer le gif » si le début et la fin ne vont pas ensemble."""
        debut, fin = self.champ_debut.value(), self.champ_fin.value()
        if fin <= debut:
            self.alerte_gif.setText("> la fin de l'extrait doit être après le début")
            self.bouton_creer_gif.setEnabled(False)
            return
        self.bouton_creer_gif.setEnabled(True)
        duree = fin - debut
        if duree > 30:
            self.alerte_gif.setText(
                f"> extrait de {duree_lisible(duree)} : le gif risque d'être très lourd")
        else:
            self.alerte_gif.setText(f"> extrait de {duree:.1f} s".replace(".", ","))

    def _lancer_gif(self):
        index = max(0, self.choix_video.currentIndex())
        self._lancer(
            convertir_gif,
            {"video": self.videos[index], "debut": self.champ_debut.value(),
             "fin": self.champ_fin.value(), "largeur": self.champ_largeur.value(),
             "ips": self.champ_ips.value()},
            "> conversion en gif", self._gif_termine, self.page_gif,
        )

    def _gif_termine(self, r: dict):
        self._afficher_resultat(
            "> gif créé",
            taille_lisible(r["taille"]),
            f"{r['ips']} images/s · {r['largeur']} px de large max.\n{r['fichier']}",
            r["fichier"],
        )

    # ------------------------------------------------------------------
    # Écran 5 : conversion en cours
    # ------------------------------------------------------------------

    def _construire_travail(self):
        page, disposition = self._nouvelle_page()
        self.titre_travail = etiquette("", "titre")
        self.detail_travail = etiquette("", "discret")
        self.barre = QProgressBar()
        self.barre.setTextVisible(False)
        annuler = bouton("[annuler]", "lien")
        annuler.clicked.connect(self._annuler)

        disposition.addStretch(1)
        disposition.addWidget(self.titre_travail)
        disposition.addSpacing(22)
        disposition.addWidget(self.barre)
        disposition.addSpacing(12)
        disposition.addWidget(self.detail_travail)
        disposition.addStretch(1)
        disposition.addLayout(self._barre_du_bas(annuler, None))
        return page

    def _lancer(self, fonction, parametres: dict, titre: str, quand_reussi, page_retour):
        """Lance une conversion en arrière-plan et affiche l'écran de progression."""
        self.titre_travail.setText(titre)
        self.detail_travail.setText("")
        self.barre.setRange(0, 100)
        self.barre.setValue(0)
        self._page_retour = page_retour

        tache = Tache(fonction, parametres, self)
        tache.progression.connect(self._sur_progression)
        tache.reussite.connect(quand_reussi)
        tache.echec.connect(self._sur_echec)
        tache.annulee.connect(lambda: self.pile.setCurrentWidget(page_retour))
        tache.finished.connect(self._tache_finie)
        self.tache = tache
        self.pile.setCurrentWidget(self.page_travail)
        tache.start()

    def _sur_progression(self, pourcentage: int, texte: str):
        texte = texte.lower()
        if pourcentage < 0:
            self.barre.setRange(0, 0)  # barre « en attente » (avancement inconnu)
            self.detail_travail.setText(texte)
        else:
            self.barre.setRange(0, 100)
            self.barre.setValue(pourcentage)
            self.detail_travail.setText(f"{texte}  {pourcentage} %")

    def _tache_finie(self):
        if self.tache is not None:
            self.tache.deleteLater()
            self.tache = None

    def _annuler(self):
        if self.tache is not None:
            self.detail_travail.setText("annulation…")
            self.tache.annuler()

    # ------------------------------------------------------------------
    # Écran 6 : résultat (ou erreur)
    # ------------------------------------------------------------------

    def _construire_resultat(self):
        page, disposition = self._nouvelle_page()
        self.titre_resultat = etiquette("", "titre")
        self.resume_resultat = etiquette("", "resume")
        self.detail_resultat = etiquette("", "discret", retour_ligne=True)
        self.detail_resultat.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bouton_ouvrir = bouton("ouvrir le dossier →", "primaire")
        self.bouton_ouvrir.clicked.connect(self._ouvrir_dossier)
        self.bouton_reessayer = bouton("réessayer")
        self.bouton_reessayer.clicked.connect(
            lambda: self.pile.setCurrentWidget(self._page_retour or self.page_accueil))
        recommencer = bouton("recommencer")
        recommencer.clicked.connect(self.recommencer)

        disposition.addStretch(1)
        disposition.addWidget(self.titre_resultat)
        disposition.addSpacing(14)
        disposition.addWidget(self.resume_resultat)
        disposition.addSpacing(10)
        disposition.addWidget(self.detail_resultat)
        disposition.addSpacing(32)
        disposition.addLayout(self._barre_du_bas(
            self.bouton_ouvrir, self.bouton_reessayer, recommencer, None))
        disposition.addStretch(1)
        return page

    def _afficher_resultat(self, titre, resume, detail, a_ouvrir):
        self.titre_resultat.setText(titre)
        self.resume_resultat.setText(resume)
        self.resume_resultat.setVisible(bool(resume))
        self.detail_resultat.setText(detail)
        self._a_ouvrir = Path(a_ouvrir) if a_ouvrir else None
        self.bouton_ouvrir.setVisible(self._a_ouvrir is not None)
        self.bouton_reessayer.setVisible(False)
        self.pile.setCurrentWidget(self.page_resultat)

    def _sur_echec(self, message: str):
        self._afficher_resultat("> erreur", "", message, None)
        self.bouton_reessayer.setVisible(True)

    def _ouvrir_dossier(self):
        if self._a_ouvrir is None:
            return
        try:
            ouvrir_dans_explorateur(self._a_ouvrir)
        except OSError:
            QMessageBox.warning(self, NOM_APPLICATION, "Impossible d'ouvrir le dossier.")

    # ------------------------------------------------------------------
    # Mise à jour (bandeau discret en bas de la fenêtre)
    # ------------------------------------------------------------------

    def _construire_bandeau_maj(self):
        bandeau = QFrame()
        bandeau.setObjectName("bandeau")
        ligne = QHBoxLayout(bandeau)
        ligne.setContentsMargins(MARGE, 10, MARGE, 10)
        ligne.setSpacing(14)
        self.texte_maj = etiquette("")
        self.bouton_maj = bouton("mettre à jour", "primaire")
        self.bouton_maj.clicked.connect(self._installer_mise_a_jour)
        self.bouton_plus_tard = bouton("[plus tard]", "lien")
        self.bouton_plus_tard.clicked.connect(lambda: self.bandeau_maj.hide())
        ligne.addWidget(self.texte_maj, 1)
        ligne.addWidget(self.bouton_plus_tard)
        ligne.addWidget(self.bouton_maj)
        bandeau.hide()

        self.infos_maj = None
        self.relais_maj = RelaisMiseAJour(self)
        self.relais_maj.trouvee.connect(self._mise_a_jour_trouvee)
        self.relais_maj.progression.connect(
            lambda p, t: self.texte_maj.setText(
                f"> {t.lower()} {p} %" if p >= 0 else f"> {t.lower()}"))
        self.relais_maj.prete.connect(self._mise_a_jour_prete)
        self.relais_maj.echec.connect(self._mise_a_jour_echouee)
        return bandeau

    def _verifier_mise_a_jour(self):
        """Interroge GitHub en arrière-plan (la fenêtre reste utilisable)."""
        def travail():
            infos = mise_a_jour.verifier()
            if infos:
                self.relais_maj.trouvee.emit(infos)
        # « daemon » : ce fil ne retarde jamais la fermeture de l'application
        threading.Thread(target=travail, daemon=True).start()

    def _mise_a_jour_trouvee(self, infos: dict):
        self.infos_maj = infos
        self.texte_maj.setText(f"> nouvelle version disponible : v{infos['version']}")
        self.bouton_maj.setText("mettre à jour")
        self.bouton_maj.setEnabled(True)
        self.bouton_plus_tard.show()
        self.bandeau_maj.show()

    def _installer_mise_a_jour(self):
        infos = self.infos_maj
        if not infos:
            return
        # Depuis le code Python (ou sans .zip joint) : on ouvre simplement la page GitHub
        if not mise_a_jour.est_installee() or not infos.get("zip"):
            QDesktopServices.openUrl(QUrl(mise_a_jour.PAGE_VERSIONS))
            return
        if self.tache is not None:
            QMessageBox.information(self, NOM_APPLICATION,
                                    "Attends la fin de la conversion en cours pour mettre à jour.")
            return

        self.bouton_maj.setEnabled(False)
        self.bouton_plus_tard.hide()
        self.texte_maj.setText("> téléchargement…")

        def travail():
            try:
                preparation = mise_a_jour.telecharger_et_preparer(
                    infos["zip"], self.relais_maj.progression.emit, lambda: False)
            except ErreurConversion as erreur:
                self.relais_maj.echec.emit(str(erreur))
            except Exception as erreur:
                self.relais_maj.echec.emit(f"La mise à jour a échoué : {erreur}")
            else:
                self.relais_maj.prete.emit(preparation)
        threading.Thread(target=travail, daemon=True).start()

    def _mise_a_jour_prete(self, preparation: dict):
        """La nouvelle version est prête : on lance le remplacement et on ferme."""
        try:
            mise_a_jour.lancer_remplacement(preparation)
        except Exception as erreur:
            self._mise_a_jour_echouee(str(erreur))
            return
        self.texte_maj.setText("> redémarrage…")
        QTimer.singleShot(300, QApplication.instance().quit)

    def _mise_a_jour_echouee(self, message: str):
        QMessageBox.warning(self, NOM_APPLICATION, message)
        self.texte_maj.setText("> la mise à jour n'a pas pu être installée")
        self.bouton_maj.setText("réessayer")
        self.bouton_maj.setEnabled(True)
        self.bouton_plus_tard.show()

    # ------------------------------------------------------------------
    # Recommencer / fermer
    # ------------------------------------------------------------------

    def recevoir_fichiers(self, chemins):
        """Fichiers choisis avec [parcourir] ou glissés sur l'icône du .exe :
        ils sont mis « en attente » et on clique ensuite sur l'action voulue."""
        images, videos, _ = trier_fichiers(chemins)
        if not images and not videos:
            self._afficher_etat("> ce type de fichier n'est pas pris en charge")
            return
        self.en_attente = images + videos
        # Les cartes compatibles s'allument, les autres s'estompent
        for carte in self.cartes:
            carte.definir_etat("attente" if carte.accepte(self.en_attente) else "inactif")
        self.lien_parcourir.hide()
        self.lien_vider.show()
        self._etat_par_defaut()

    def recommencer(self):
        """Vide tout et revient aux trois cartes."""
        self._arreter_miniatures()
        self.images, self.videos = [], []
        self.liste_pdf.clear()
        self._vider_attente()
        self.pile.setCurrentWidget(self.page_accueil)

    def closeEvent(self, evenement):
        if self.tache is not None and self.tache.isRunning():
            reponse = QMessageBox.question(
                self, NOM_APPLICATION,
                "Une conversion est en cours. Veux-tu vraiment quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reponse != QMessageBox.StandardButton.Yes:
                evenement.ignore()
                return
            self.tache.annuler()
            self.tache.wait(15000)
        self._arreter_miniatures()
        evenement.accept()
