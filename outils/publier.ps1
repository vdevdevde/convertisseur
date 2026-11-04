# ================================================================
#  Publie une nouvelle version de Convertisseur sur GitHub.
#
#  Avant de lancer : augmente VERSION dans convertisseur\__init__.py
#  (ex. 1.0.0 -> 1.1.0) et enregistre tes modifications avec git.
#
#  Ce script :
#    1. fabrique l'application (.exe) ;
#    2. la met dans un fichier .zip ;
#    3. crée la « Release » sur GitHub avec ce .zip.
#  Les applications déjà installées proposeront alors la mise à jour.
# ================================================================
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$gh = 'C:\Program Files\GitHub CLI\gh.exe'
if (-not (Test-Path $gh)) { $gh = 'gh' }

function Arret($message) {
    Write-Host ''
    Write-Host "ERREUR : $message" -ForegroundColor Red
    exit 1
}

# --- Lire le numéro de version dans le code ---
$texte = Get-Content 'convertisseur\__init__.py' -Raw -Encoding UTF8
if ($texte -notmatch 'VERSION\s*=\s*"([0-9.]+)"') { Arret 'VERSION introuvable dans convertisseur\__init__.py' }
$version = $Matches[1]
$etiquette = "v$version"
Write-Host "Publication de Convertisseur $version" -ForegroundColor Cyan

# --- Vérifications ---
& $gh auth status *> $null
if ($LASTEXITCODE -ne 0) { Arret "Tu n'es pas connecté à GitHub. Lance : gh auth login" }

$modifs = git status --porcelain
if ($modifs) { Arret "Des modifications ne sont pas enregistrées (commit). Fais d'abord : git add -A puis git commit -m `"...`"" }

git rev-parse -q --verify "refs/tags/$etiquette" *> $null
if ($LASTEXITCODE -eq 0) { Arret "La version $version existe déjà. Augmente VERSION dans convertisseur\__init__.py." }

$notes = Read-Host 'Qu''est-ce qui change dans cette version ? (une phrase)'
if (-not $notes) { $notes = "Version $version" }

# --- 1. Fabrication ---
Write-Host '[1/3] Fabrication de l''application...'
cmd /c "construire.bat < nul"
if ($LASTEXITCODE -ne 0) { Arret 'La fabrication a échoué.' }

# --- 2. Archive .zip (contient le dossier Convertisseur) ---
Write-Host '[2/3] Création du fichier .zip...'
$zip = "dist\Convertisseur-$version.zip"
if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path 'dist\Convertisseur' -DestinationPath $zip -CompressionLevel Optimal

# --- 3. Envoi sur GitHub ---
Write-Host '[3/3] Envoi sur GitHub...'
git push
git tag $etiquette
git push origin $etiquette
& $gh release create $etiquette $zip --title "Convertisseur $version" --notes $notes
if ($LASTEXITCODE -ne 0) { Arret 'La création de la version sur GitHub a échoué.' }

Write-Host ''
Write-Host "Terminé ! La version $version est en ligne." -ForegroundColor Green
