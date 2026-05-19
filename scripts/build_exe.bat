@echo off
python -m pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --name DigitalTrajectoryPro run.py
pause
