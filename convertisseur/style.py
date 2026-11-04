"""Le style de l'application : uniquement du noir, du blanc et des gris.

Deux jeux de couleurs : CLAIR (fond blanc, texte noir) et SOMBRE (l'inverse).
L'application suit automatiquement le réglage clair / sombre de Windows.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette

CLAIR = {
    "fond": "#FFFFFF",
    "texte": "#111111",
    "doux": "#6E6E6E",        # texte secondaire
    "trait": "#CFCFCF",       # bordures fines
    "survol": "#F4F4F4",      # fond au survol
    "appui": "#E8E8E8",       # fond quand on clique
    "piste": "#E6E6E6",       # fond des barres et curseurs
    "accent": "#111111",      # bouton principal
    "accent_survol": "#3A3A3A",
    "sur_accent": "#FFFFFF",  # texte sur le bouton principal
}

SOMBRE = {
    "fond": "#121212",
    "texte": "#F2F2F2",
    "doux": "#9A9A9A",
    "trait": "#3A3A3A",
    "survol": "#1E1E1E",
    "appui": "#2A2A2A",
    "piste": "#2E2E2E",
    "accent": "#F2F2F2",
    "accent_survol": "#CFCFCF",
    "sur_accent": "#121212",
}


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

    QLabel#titre {{ font-size: 20pt; font-weight: 300; }}
    QLabel#titreZone {{ font-size: 17pt; font-weight: 300; }}
    QLabel#resume {{ font-size: 15pt; }}
    QLabel#actionTitre {{ font-size: 11.5pt; font-weight: 600; }}
    QLabel#discret {{ color: {c['doux']}; }}
    QLabel#etiquette {{ font-weight: 600; }}

    /* Boutons : rectangles simples, coins légèrement arrondis */
    QPushButton {{
        background: {c['fond']};
        color: {c['texte']};
        border: 1px solid {c['trait']};
        border-radius: 6px;
        padding: 9px 20px;
    }}
    QPushButton:hover {{ background: {c['survol']}; border-color: {c['doux']}; }}
    QPushButton:pressed {{ background: {c['appui']}; }}
    QPushButton:disabled {{ color: {c['doux']}; border-color: {c['piste']}; }}

    QPushButton#primaire {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border: 1px solid {c['accent']};
        font-weight: 600;
    }}
    QPushButton#primaire:hover {{ background: {c['accent_survol']}; border-color: {c['accent_survol']}; }}
    QPushButton#primaire:disabled {{ background: {c['piste']}; border-color: {c['piste']}; color: {c['doux']}; }}

    QPushButton#lien {{
        background: transparent;
        border: none;
        color: {c['doux']};
        text-decoration: underline;
        padding: 4px 6px;
    }}
    QPushButton#lien:hover {{ color: {c['texte']}; }}

    QPushButton#action {{ text-align: left; padding: 0; }}
    QPushButton#action:hover {{ border-color: {c['texte']}; }}

    /* Boutons à choix unique (Originale / 1920 px / 1280 px) */
    QPushButton#choix {{ padding: 7px 16px; }}
    QPushButton#choix:checked {{
        background: {c['accent']};
        color: {c['sur_accent']};
        border-color: {c['accent']};
    }}

    /* Fine barre de progression */
    QProgressBar {{
        background: {c['piste']};
        border: none;
        border-radius: 1px;
        min-height: 3px;
        max-height: 3px;
    }}
    QProgressBar::chunk {{ background: {c['texte']}; border-radius: 1px; }}

    /* Curseur « Qualité » */
    QSlider::groove:horizontal {{ height: 2px; background: {c['piste']}; }}
    QSlider::sub-page:horizontal {{ background: {c['texte']}; }}
    QSlider::handle:horizontal {{
        background: {c['texte']};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}

    /* Champs de saisie */
    QSpinBox, QDoubleSpinBox, QComboBox {{
        background: {c['fond']};
        border: 1px solid {c['trait']};
        border-radius: 6px;
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
        border: 1px solid {c['trait']};
        border-radius: 6px;
        padding: 10px;
        outline: none;
    }}
    QListWidget::item {{ border: 1px solid transparent; border-radius: 4px; padding: 4px; }}
    QListWidget::item:hover {{ background: {c['survol']}; }}
    QListWidget::item:selected {{ background: {c['survol']}; border-color: {c['texte']}; }}

    /* Barres de défilement discrètes */
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {c['trait']}; border-radius: 3px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    /* Bandeau « nouvelle version » en bas de la fenêtre */
    QFrame#bandeau {{ border-top: 1px solid {c['trait']}; }}
    QFrame#bandeau QPushButton#primaire {{ padding: 6px 14px; }}

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
