"""
Główny punkt wejścia do projektu ManulDetector.
Domyślnie uruchamia scraper zdjęć manuli z manulization.com (100 zdjęć na osobnika).
Do kadrowania YOLOv8 służy plik crop.py.
"""
from scraper import main as run_scraper

if __name__ == "__main__":
    run_scraper()
