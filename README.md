# Convertisseur

Dépose tes fichiers directement sur l'action voulue (ou clique dessus pour parcourir) :

| Fichiers déposés | Actions proposées |
|---|---|
| Images (JPG, PNG, WEBP, HEIC) | Créer un PDF · Réduire la taille |
| Vidéos (MP4, MOV, AVI) | Convertir en GIF |

Les originaux ne sont jamais modifiés. Les nouveaux fichiers sont créés à côté :
`images.pdf`, le dossier `reduites\`, `ma-video.gif`.

## Lancer l'application

Double-clique sur **`dist\Convertisseur\Convertisseur.exe`**.
Pour l'avoir sur le Bureau : clic droit sur le fichier → *Afficher d'autres options* →
*Envoyer vers* → *Bureau (créer un raccourci)*.

⚠️ Garde le `.exe` dans son dossier `Convertisseur` : il a besoin du dossier `_internal`
qui l'accompagne. Pour le copier ailleurs, copie tout le dossier `dist\Convertisseur`.

## Modifier le code

| Fichier | Rôle |
|---|---|
| `convertisseur\conversions.py` | Les conversions (PDF, réduction, GIF) |
| `convertisseur\fenetre.py` | Les écrans de l'application |
| `convertisseur\style.py` | Les couleurs et le style (clair / sombre) |
| `convertisseur\widgets.py` | La zone de dépôt et les boutons |
| `convertisseur\fichiers.py` | Outils : types de fichiers, tailles, noms |
| `convertisseur\taches.py` | Le travail en arrière-plan (fenêtre jamais figée) |

- Tester sans reconstruire : `.venv\Scripts\python.exe lancer.py`
- Reconstruire le `.exe` : double-clique sur `construire.bat`

## Mises à jour

Au démarrage, l'application regarde sur GitHub si une version plus récente existe.
Si oui, un bandeau apparaît en bas : **Mettre à jour** télécharge la nouvelle version,
remplace les fichiers et relance l'application. Sans Internet, rien ne s'affiche.

### Publier une nouvelle version

1. Fais tes modifications et vérifie-les avec `.venv\Scripts\python.exe lancer.py`.
2. Dans `convertisseur\__init__.py`, augmente `VERSION` (ex. `1.0.0` → `1.1.0`).
3. Enregistre les modifications avec git :
   ```
   git add -A
   git commit -m "Ce que j'ai changé"
   ```
4. Double-clique sur `publier.bat`. Il fabrique le `.exe`, le compresse en `.zip`
   et crée la version sur GitHub.

Toutes les applications installées proposeront la mise à jour au prochain démarrage.

## Installer sur un autre PC

Sur la page GitHub du projet → **Releases** → télécharge `Convertisseur-x.y.z.zip`,
décompresse-le, puis lance `Convertisseur\Convertisseur.exe`.

En cas de souci, les erreurs sont notées dans `%LOCALAPPDATA%\Convertisseur\journal.txt`.
