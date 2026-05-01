@echo off
echo Setting up quant project virtual environment...

python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete! To activate later, run:
echo   venv\Scripts\activate
echo.
echo To run the pipeline:
echo   python main.py
