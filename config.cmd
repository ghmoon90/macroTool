@echo off
REM config python environment
python -m pip install --upgrade pip
pip freeze>to_remove
pip uninstall -y -r to_remove
pip install -r requirements.txt
del to_remove