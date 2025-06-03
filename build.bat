@echo off
python -m PyInstaller ^
--clean ^
--onefile ^
--windowed ^
--add-data "assets;assets" ^
--hidden-import ttkbootstrap ^
--hidden-import PIL ^
--hidden-import matplotlib ^
--hidden-import pandas ^
--hidden-import reportlab ^
--collect-data ttkbootstrap ^
--name "Thunderstorm Bill Generator" ^
launcher.py 