@echo off
REM ================================================================
REM FilterMate V01  -  Production Video Complete (One-Click)
REM ================================================================
REM
REM  Pre-requis AVANT de lancer ce script :
REM    1. QGIS ouvert avec un projet contenant les couches :
REM       - departements_france (Shapefile, ~100 entites)
REM       - communes_france (Shapefile, ~35 000 entites)
REM    2. OBS Studio ouvert avec WebSocket Server active :
REM       Outils > WebSocket Server Settings > Enable WebSocket Server
REM       (port 4455, pas de mot de passe par defaut)
REM    3. Python 3.10+ dans le PATH
REM
REM  Le script va :
REM    Etape 1  -  Verifier les prerequis
REM    Etape 2  -  Generer la narration TTS (14 fichiers MP3)
REM    Etape 3  -  Generer les diagrammes (21 HTML + 21 PNG)
REM    Etape 4  -  Calibrer les positions UI (interactif)
REM    Etape 5  -  Configurer OBS (scenes + sources)
REM    Etape 6  -  Enregistrer les 14 sequences (QGIS + OBS)
REM    Etape 7  -  Assembler la video finale
REM
REM  Sortie : output\final\filtermate_v01_final.mp4
REM ================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo  ===================================================
echo   FilterMate V01  -  Production Video Automatisee
echo   Installation et Premier Pas (7 min, 14 sequences)
echo  ===================================================
echo.

REM -- Etape 1 : Prerequis ------------------------------------------

echo  [1/7] Verification des prerequis...
echo.

set ERRORS=0

python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo    ok  Python %%v
) else (
    echo    !!  Python non trouve. Installez Python 3.10+ et ajoutez-le au PATH.
    set /a ERRORS+=1
)

ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  FFmpeg
) else (
    echo    !!  FFmpeg non trouve. Installez : winget install ffmpeg
    set /a ERRORS+=1
)

pip show pyautogui >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  pyautogui
) else (
    echo    ..  Installation de pyautogui...
    pip install pyautogui --quiet 2>nul
)

pip show click >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  click
) else (
    pip install click --quiet 2>nul
)

pip show pyyaml >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  pyyaml
) else (
    pip install pyyaml --quiet 2>nul
)

pip show edge-tts >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  edge-tts
) else (
    echo    ..  Installation de edge-tts...
    pip install edge-tts --quiet 2>nul
)

pip show obsws-python >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  obsws-python
) else (
    echo    ..  Installation de obsws-python...
    pip install obsws-python --quiet 2>nul
)

pip show Pillow >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  Pillow
) else (
    pip install Pillow --quiet 2>nul
)

pip show mutagen >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  mutagen
) else (
    pip install mutagen --quiet 2>nul
)

pip show playwright >nul 2>&1
if %errorlevel% equ 0 (
    echo    ok  playwright
) else (
    echo    ..  Installation de playwright + chromium...
    pip install playwright --quiet 2>nul
    python -m playwright install chromium --quiet 2>nul
)

echo.

if !ERRORS! gtr 0 (
    echo  [ERREUR] !ERRORS! prerequis manquants. Corrigez et relancez.
    echo.
    pause
    exit /b 1
)

echo    Tous les prerequis sont OK.
echo.

REM -- Etape 2 : Narration TTS -------------------------------------

echo  [2/7] Generation de la narration TTS (14 sequences)...
echo.

if exist "output\narration\v01\v01_s00_narration.mp3" (
    echo    Les fichiers narration existent deja. Passer ? [O/n]
    set /p SKIP_NARR="    > "
    if /i "!SKIP_NARR!"=="n" (
        python run.py --narration --video v01
    ) else (
        echo    .. Narration existante conservee.
    )
) else (
    python run.py --narration --video v01
)
echo.

REM -- Etape 3 : Diagrammes ----------------------------------------

echo  [3/7] Generation des diagrammes HTML + PNG (21 diagrammes)...
echo.

if exist "output\diagrams\v01_install_flow.png" (
    echo    Les diagrammes existent deja. Passer ? [O/n]
    set /p SKIP_DIAG="    > "
    if /i "!SKIP_DIAG!"=="n" (
        python run.py --diagrams
    ) else (
        echo    .. Diagrammes existants conserves.
    )
) else (
    python run.py --diagrams
)
echo.

REM -- Etape 4 : Calibration UI ------------------------------------

echo  [4/7] Calibration des positions UI...
echo.
echo    IMPORTANT : QGIS doit etre ouvert avec FilterMate visible.
echo    Le script va vous demander de cliquer sur des elements de l'interface.
echo.
echo    Lancer la calibration ? [O/n]
set /p DO_CALIB="    > "
if /i "!DO_CALIB!"=="n" (
    echo    .. Calibration ignoree ^(positions existantes conservees^).
) else (
    python run.py --calibrate
)
echo.

REM -- Etape 5 : Configuration OBS ---------------------------------

echo  [5/7] Configuration automatique d'OBS...
echo.
echo    IMPORTANT : OBS Studio doit etre ouvert avec WebSocket active.
echo    Outils ^> WebSocket Server Settings ^> Enable
echo.
echo    Configurer OBS ? [O/n]
set /p DO_OBS="    > "
if /i "!DO_OBS!"=="n" (
    echo    .. Configuration OBS ignoree.
) else (
    python run.py --setup-obs
)
echo.

REM -- Etape 6 : Enregistrement ------------------------------------

echo  [6/7] Enregistrement des 14 sequences V01...
echo.
echo    ATTENTION : Ne touchez pas a la souris ni au clavier pendant
echo    l'enregistrement ! PyAutoGUI va piloter QGIS automatiquement.
echo.
echo    Securite : deplacez la souris dans le coin haut-gauche pour
echo    interrompre immediatement [PyAutoGUI FAILSAFE].
echo.
echo    Duree estimee : ~7 minutes + transitions.
echo.
echo    Pret ? Appuyez sur une touche pour commencer...
pause >nul

python run.py --all --video v01
echo.

REM -- Etape 7 : Assemblage final ----------------------------------

echo  [7/7] Assemblage de la video finale...
echo.

ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    python run.py --assemble --video v01
) else (
    echo    [SKIP] FFmpeg non disponible, assemblage ignore.
    echo    Installez FFmpeg et relancez : python run.py --assemble --video v01
)

echo.
echo  ===================================================
echo   PRODUCTION TERMINEE
echo  ===================================================
echo.
echo   Fichiers generes :
echo.
echo     Narration :  output\narration\v01\  (14 MP3)
echo     Diagrammes : output\diagrams\       (21 HTML + 21 PNG)
echo     Clips :      Voir dossier OBS
echo     Video :      output\final\filtermate_v01_final.mp4
echo.
echo   Duree totale narration : ~5m30
echo   Sequences : 14 (Hook a Conclusion)
echo.
echo  ===================================================
echo.
pause
