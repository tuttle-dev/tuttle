import os

os.system(
    "pyinstaller app/Tuttle.py --noconsole --noconfirm --onefile --add-data 'tuttle_tests/data/TuttleDemo-TimeTracking.ics:.'"
)
