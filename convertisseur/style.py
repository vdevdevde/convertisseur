"""Le style de l'application, façon « terminal » : uniquement du noir, du blanc
et des gris, une police à chasse fixe, des coins presque droits.

Deux jeux de couleurs : SOMBRE (fond noir, texte blanc) et CLAIR (l'inverse).
L'application suit automatiquement le réglage clair / sombre de Windows.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QPalette

# Polices à chasse fixe, par ordre de préférence (Consolas existe sur tous les Windows)
POLICES = ["Cascadia Mono", "JetBrains Mono", "Consolas", "Courier New"]

SOMBRE = {
    "fond": "#0A0A0A",
    "carte": "#161616",       # fond d'une carte survolée
    "texte": "#EDEDED",
    "doux": "#7C7C7C",        # texte secondaire
    "trait": "#3A3A3A",       # bordures fines
    "survol": "#1A1A1A",
    "appui": "#262626",
    "piste": "#2A2A2A",       # fond des barres et curseurs
    "accent": "#EDEDED",      # bouton principal
    "accent_survol": "#C8C8C8",
    "sur_accent": "#0A0A0A",  # texte sur le bouton principal
}

CLAIR = {
    "fond": "#FFFFFF",
    "carte": "#F3F3F3",
    "texte": "#111111",
    "doux": "#767676",
    "trait": "#C4C4C4",
    "survol": "#F3F3F3",
    "appui": "#E6E6E6",
    "piste": "#E4E4E4",
    "accent": "#111111",
    "accent_survol": "#3A3A3A",
    "sur_accent": "#FFFFFF",
}


def police_monospace(taille: float = 10) -> QFont:
    """La première police à chasse fixe disponible sur ce PC."""
    disponibles = set(QFontDatabase.families())
    for nom in POLICES:
        if nom in disponibles:
            return QFont(nom, taille)
    police = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    police.setPointSizeF(taille)
    return police


def mode_sombre_actif() -> bool:
    """Vrai si Windows est réglé en mode sombre."""
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def feuille_de_style(c: dict) -> str:
    """Construit la feuille de style (comme du CSS) avec les couleurs données."""
    return f"""
    QWidget {{
        background: {c['fond']};
        color: {c['texte']};
    }}
    QLabel {{ background: transparent; }}

    QLabel#logo {{ font-weight: 700; font-size: 10.5pt; }}
    QLabel#titre {{ font-size: 17pt; font-weight: 700; }}
    QLabel#titreCarte {{ font-size: 12pt; font-weight: 700; }}
    QLabel#resume {{ font-size: 14pt; }}
    QLabel#discret {{ color: {c['doux']}; }}
    QLabel#pied {{ color: {c['doux']}; font-size: 9pt; }}
    QLabel#etiquette {{ color: {c['doux']}; }}

    /* Boutons : rectangles simples, coins presque droits */
    QPushButton {{
        background: transparent;
        color: {c['texte']};
        border: 1px solid {c['trait']};
        border-radius: 2px;
        padding: 8px 18px;
    }}
    QPushButton:hover {{ background: {c['survol']}; border-color: {c['texte']}; }}
    QPushButton:pressed {{ background: {c['appui']}; }}
    QPushButton:disabled {{ color: {c['doux']}; border-color: {c['piste']}; }}

    QPushButton#primaire {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border: 1px solid {c['accent']};
        font-weight: 700;
    }}
    QPushButton#primaire:hover {{ background: {c['accent_survol']}; border-color: {c['accent_survol']}; }}
    QPushButton#primaire:disabled {{ background: {c['piste']}; border-color: {c['piste']}; color: {c['doux']}; }}

    /* Liens façon [parcourir] */
    QPushButton#lien {{
        background: transparent;
        border: none;
        color: {c['texte']};
        text-decoration: underline;
        padding: 2px 0;
    }}
    QPushButton#lien:hover {{ color: {c['doux']}; }}

    /* Boutons à choix unique (originale / 1920 px / 1280 px) */
    QPushButton#choix {{ padding: 6px 14px; }}
    QPushButton#choix:checked {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border-color: {c['accent']};
    }}

    /* Fine barre de progression */
    QProgressBar {{
        background: {c['piste']};
        border: none;
        min-height: 2px;
        max-height: 2px;
    }}
    QProgressBar::chunk {{ background: {c['texte']}; }}

    /* Curseur « qualité » */
    QSlider::groove:horizontal {{ height: 1px; background: {c['trait']}; }}
    QSlider::sub-page:horizontal {{ background: {c['texte']}; }}
    QSlider::handle:horizontal {{
        background: {c['texte']};
        width: 10px;
        height: 14px;
        margin: -7px 0;
        border-radius: 1px;
    }}

    /* Champs de saisie */
    QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {c['fond']};
        border: 1px solid {c['trait']};
        border-radius: 2px;
        padding: 6px 8px;
        min-width: 90px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{ border-color: {c['texte']}; }}
    /* Champs épurés, sans petites flèches : on tape la valeur,
       ou on utilise la molette de la souris / les flèches du clavier */
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
    QComboBox QAbstractItemView {{
        background: {c['fond']};
        border: 1px solid {c['trait']};
        selection-background-color: {c['survol']};
        selection-color: {c['texte']};
    }}

    /* Liste des miniatures */
    QListWidget {{
        background: {c['fond']};
        border: 1px dashed {c['trait']};
        border-radius: 3px;
        padding: 10px;
        outline: none;
    }}
    QListWidget::item {{ border: 1px solid transparent; padding: 4px; }}
    QListWidget::item:hover {{ background: {c['survol']}; }}
    QListWidget::item:selected {{ background: {c['survol']}; border-color: {c['texte']}; }}

    /* Ligne de séparation */
    QFrame#ligne {{ background: {c['trait']}; border: none; max-height: 1px; min-height: 1px; }}

    /* Bandeau « nouvelle version » en bas de la fenêtre */
    QFrame#bandeau {{ border-top: 1px solid {c['trait']}; }}
    QFrame#bandeau QPushButton#primaire {{ padding: 5px 12px; }}

    /* Barres de défilement discrètes */
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['trait']}; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QToolTip {{
        background: {c['texte']};
        color: {c['fond']};
        border: none;
        padding: 4px 8px;
    }}
    """


def appliquer_theme(application) -> dict:
    """Applique le thème clair ou sombre selon Windows. Renvoie les couleurs choisies."""
    c = SOMBRE if mode_sombre_actif() else CLAIR

    # La « palette » sert aux éléments que la feuille de style ne couvre pas
    # (boîtes de dialogue, menus…). Aucune couleur : que des gris.
    palette = QPalette()
    for role, cle in (
        (QPalette.ColorRole.Window, "fond"),
        (QPalette.ColorRole.Base, "fond"),
        (QPalette.ColorRole.AlternateBase, "survol"),
        (QPalette.ColorRole.Button, "fond"),
        (QPalette.ColorRole.WindowText, "texte"),
        (QPalette.ColorRole.Text, "texte"),
        (QPalette.ColorRole.ButtonText, "texte"),
        (QPalette.ColorRole.ToolTipBase, "texte"),
        (QPalette.ColorRole.ToolTipText, "fond"),
        (QPalette.ColorRole.PlaceholderText, "doux"),
        (QPalette.ColorRole.Highlight, "appui"),
        (QPalette.ColorRole.HighlightedText, "texte"),
        (QPalette.ColorRole.Link, "texte"),
        (QPalette.ColorRole.Mid, "trait"),
    ):
        palette.setColor(role, QColor(c[cle]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["doux"]))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["doux"]))

    application.setPalette(palette)
    application.setStyleSheet(feuille_de_style(c))
    return c
