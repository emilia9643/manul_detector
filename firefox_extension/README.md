# Manul Twitter Image Extractor (Firefox Extension) v1.2

Wtyczka do przeglądarki Mozilla Firefox do masowego wyciągania i pobierania zdjęć w oryginalnej jakości (`name=orig`) z Twittera/X do wybranego folderu.

## Co nowego w v1.2?
- **Wybór folderu docelowego:** Po kliknięciu na ikonę wtyczki otwiera się okienko popup, w którym możesz wpisać dowolną nazwę folderu (lub podfolderu, np. `manule/bol` czy `manul_dataset`).
- **Zapamiętywanie ostatniego folderu:** Wtyczka pamięta ostatnio wpisany folder, więc nie musisz wpisywać go za każdym razem.
- **Podgląd ścieżki i statusu na żywo:** Widzisz dokładną ścieżkę zapisu (`~/Pobrane/<twój_folder>/img_XXX.jpg`) oraz pasek postępu pobierania.
- **Przycisk „Wyczyść”:** Możliwość wyzerowania zebranej kolejki bez pobierania.

---

## Jak zaktualizować wtyczkę w Firefoxie?

1. Wpisz w pasku adresu Firefoxa:
   ```text
   about:debugging#/runtime/this-firefox
   ```
2. Znajdź **Manul Twitter Image Extractor** i kliknij **„Przeładuj”** (*Reload*).

---

## Jak używać?

1. Otwórz Twitter/X i przewijaj posty (licznik na ikonie rośnie w czasie rzeczywistym).
2. **Kliknij ikonę wtyczki** – otworzy się okienko:
   - Zobaczysz liczbę zebranych unikalnych zdjęć.
   - Wpisz nazwę folderu w polu **„Folder docelowy”** (np. `manule_bol` lub `manul_dataset`).
   - Kliknij **„Pobierz zdjęcia”**.
3. Zdjęcia zostaną zapisane w:
   ```text
   ~/Pobrane/<twoj_folder>/img_001.jpg
   ~/Pobrane/<twoj_folder>/img_002.jpg
   ...
   ```
