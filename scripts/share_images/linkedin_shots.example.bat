@echo off
call "C:\Program Files\QGIS 4.2.3\bin\o4w_env.bat"
call "C:\Program Files\QGIS 4.2.3\bin\qt6_env.bat" 2>nul
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/qgis
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis\qtplugins;%OSGEO4W_ROOT%\apps\Qt6\plugins
set FM_REPO=\\wsl.localhost\Ubuntu\home\simon\dev\filter_mate-wt-site
set FM5_DATA_DIR=C:\Users\Simon\Documents\FilterMate_test_v5\data
set FM5_OUT=C:\Users\Simon\Documents\FilterMate_test_v5\linkedin_out
cd /d C:\Users\Simon\Documents\FilterMate_test_v5
start "" /min /wait "%OSGEO4W_ROOT%\bin\qgis-bin.exe" --nologo --noversioncheck --lang en --profiles-path "C:\Users\Simon\AppData\Local\Temp\fm5\profiles" --profile fm5 --code "\\wsl.localhost\Ubuntu\home\simon\dev\filter_mate-wt-site\scripts\fm5_linkedin_shots.py" > linkedin_stdout.txt 2>&1
