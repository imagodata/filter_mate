@echo off
REM Init Ollama pour l'agent FilterMate : serveur + qwen3.5:4b prechauffe a 32768.
REM Double-clic avant d'ouvrir QGIS. Laisse la fenetre "Ollama serve" ouverte.
setlocal
set MODEL=qwen3.5:4b
set OLLAMA_KEEP_ALIVE=30m

curl.exe -s -m 5 http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
  echo Demarrage d'Ollama (garde charge 30 min)...
  start "Ollama serve" /min ollama serve
) else (
  echo Ollama repond deja. NOTE : s'il a ete lance sans OLLAMA_KEEP_ALIVE=30m,
  echo relance-le a la main pour garder le modele charge entre deux messages.
)

set TRIES=0
:wait
curl.exe -s -m 5 http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
  set /a TRIES+=1
  if %TRIES% GEQ 30 (
    echo Le serveur ne demarre pas. Lance "ollama serve" a la main et relis l'erreur.
    pause
    exit /b 1
  )
  timeout /t 2 /nobreak >nul
  goto wait
)
echo Serveur OK.

ollama list | findstr /C:"%MODEL%" >nul 2>&1
if errorlevel 1 (
  echo Telechargement de %MODEL% (plusieurs Go)...
  ollama pull %MODEL%
  if errorlevel 1 (
    echo Echec du telechargement. Verifie ta connexion puis relance ce script.
    pause
    exit /b 1
  )
) else (
  echo Modele %MODEL% present.
)

echo Prechauffage a 32768 tokens (plusieurs minutes sur CPU, une seule fois)...
powershell -NoProfile -Command "$b=@{model='qwen3.5:4b';stream=$false;options=@{num_ctx=32768;num_predict=16};messages=@(@{role='user';content='dis bonjour'})} | ConvertTo-Json -Depth 5; (Invoke-RestMethod -Uri 'http://localhost:11434/api/chat' -Method Post -ContentType 'application/json' -Body $b -TimeoutSec 590).message.content"
if errorlevel 1 (
  echo Prechauffage echoue : le serveur a mis trop de temps ou le modele manque de RAM.
  echo Relance ce script ; s'il echoue encore, c'est le delai qu'il faut allonger.
  pause
  exit /b 1
)
echo.
echo Termine : modele charge. Pense aussi a monter le delai reseau de QGIS
echo (Preferences - Options - Reseau - delai d'attente, ex. 300 000 ms),
echo puis utilise l'agent avec le preset Ollama et le modele qwen3.5:4b.
pause
