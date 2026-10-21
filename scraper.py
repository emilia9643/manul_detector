import os
import re
import time
import argparse
from urllib.parse import urlparse
import requests

# Konfiguracja manuli i linków
MANULS = [
    {
        "name": "grusha",
        "url": "https://manulization.com/manuls/grusha/photos-and-videos",
    },
    {
        "name": "primula",
        "url": "https://manulization.com/manuls/primula/photos-and-videos",
    },
    {
        "name": "bol",
        "url": "https://manulization.com/manuls/boru-bol/photos-and-videos",
    },
    {
        "name": "nagomu",
        "url": "https://manulization.com/manuls/nagomu/photos-and-videos",
    },
    {
        "name": "prinsessa",
        "url": "https://manulization.com/manuls/prinsessa/photos-and-videos",
    },
]

OUTPUT_BASE_DIR = os.path.join("data", "raw")
DEFAULT_PHOTOS_PER_MANUL = 100
MAX_IMAGE_WIDTH = 1200  # Optymalny rozmiar (dobra jakość pod detekcję/kadrowanie, szybkie pobieranie)
REQUEST_DELAY = 0.2     # Przerwa między żądaniami w sekundach

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def extract_photos_and_cursor(html_text):
    """
    Wyciąga adresy URL zdjęć (pomijając filmy) oraz kursor do następnej strony.
    """
    items = html_text.split('<a class="media-squares-grid__item"')[1:]
    photo_urls = []

    for it in items:
        # Pomijamy materiały wideo
        if "play_circle" in it or "video-" in it or 'title="A video' in it:
            continue

        best_url = None
        srcset_match = re.search(r'data-gallery-srcset="([^"]+)"', it)
        src_match = re.search(r'data-gallery-src="([^"]+)"', it)

        if srcset_match:
            entries = srcset_match.group(1).split(",")
            urls_by_w = {}
            for entry in entries:
                parts = entry.strip().split()
                if len(parts) == 2:
                    try:
                        w_val = int(parts[1].replace("w", ""))
                        urls_by_w[w_val] = parts[0]
                    except ValueError:
                        continue

            candidates = [w for w in urls_by_w if w <= MAX_IMAGE_WIDTH]
            if candidates:
                best_url = urls_by_w[max(candidates)]
            elif urls_by_w:
                best_url = urls_by_w[min(urls_by_w.keys())]

        if not best_url and src_match:
            best_url = src_match.group(1)

        if best_url:
            photo_urls.append(best_url)

    # Szukamy kursora do następnej strony w turbo-frame na dole
    next_cursor = None
    cursor_match = re.search(r'<turbo-frame[^>]+src="[^"]*cursor=([a-zA-Z0-9_-]+)', html_text)
    if cursor_match:
        next_cursor = cursor_match.group(1)

    return photo_urls, next_cursor


def scrape_manul_photos(session, name, base_url, target_count, save_dir):
    """
    Pobiera określoną liczbę zdjęć dla danego manula.
    """
    os.makedirs(save_dir, exist_ok=True)
    existing_files = set(os.listdir(save_dir))

    print(f"\n==========================================")
    print(f"Rozpoczynam pobieranie: {name.upper()}")
    print(f"Cel: {target_count} zdjęć -> Folder: '{save_dir}'")
    print(f"Już pobrano wcześniej: {len(existing_files)} plików")
    print(f"==========================================")

    current_url = base_url
    cursor = None
    total_downloaded = len(existing_files)
    page_num = 1

    while total_downloaded < target_count:
        if cursor:
            page_url = f"{base_url}?cursor={cursor}&sortOrder=recentlyUploadedFirst"
        else:
            page_url = base_url

        try:
            resp = session.get(page_url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"[BŁĄD] Nie udało się pobrać strony {page_num} dla {name}: {e}")
            break

        photo_urls, next_cursor = extract_photos_and_cursor(resp.text)
        print(f"  Strona {page_num}: znaleziono {len(photo_urls)} zdjęć (bez wideo).")

        if not photo_urls and not next_cursor:
            print(f"  Brak kolejnych zdjęć na stronie.")
            break

        for img_url in photo_urls:
            if total_downloaded >= target_count:
                break

            filename = os.path.basename(urlparse(img_url).path)
            if not filename:
                continue

            filepath = os.path.join(save_dir, filename)
            if os.path.exists(filepath):
                continue

            try:
                img_resp = session.get(img_url, headers=HEADERS, timeout=20)
                img_resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)
                total_downloaded += 1
                print(f"    [{total_downloaded:03d}/{target_count}] Pobrano: {filename} ({len(img_resp.content) // 1024} KB)")
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"    [BŁĄD] Pobieranie {img_url} nie powiodło się: {e}")

        if not next_cursor or next_cursor == cursor:
            print(f"  Koniec dostępnych stron dla {name}.")
            break

        cursor = next_cursor
        page_num += 1
        time.sleep(REQUEST_DELAY)

    print(f"Podsumowanie dla {name}: {total_downloaded}/{target_count} zdjęć w folderze.")
    return total_downloaded


def main(limit=None):
    parser = argparse.ArgumentParser(description="Pobieranie zdjęć manuli z manulization.com")
    parser.add_argument("--limit", type=int, default=DEFAULT_PHOTOS_PER_MANUL, help="Liczba zdjęć na manula (domyślnie: 100)")
    parser.add_argument("--output", type=str, default=OUTPUT_BASE_DIR, help="Folder wyjściowy (domyślnie: data/raw)")
    args, unknown = parser.parse_known_args()

    target_count = limit if limit is not None else args.limit
    output_dir = args.output

    session = requests.Session()
    stats = {}
    start_time = time.time()

    print("=== MANULIZATION.COM SCRAPER ===")
    print(f"Liczba manuli do pobrania: {len(MANULS)}")
    print(f"Liczba zdjęć na osobnika: {target_count}")
    print(f"Katalog zapisu: {output_dir}")

    for manul in MANULS:
        name = manul["name"]
        url = manul["url"]
        save_dir = os.path.join(output_dir, name)
        count = scrape_manul_photos(session, name, url, target_count, save_dir)
        stats[name] = count

    elapsed = time.time() - start_time
    print("\n==========================================")
    print("ZAKOŃCZONO POBIERANIE WSZYSTKICH MANULI")
    print(f"Czas trwania: {elapsed:.1f} sekund")
    print("Liczba pobranych zdjęć wg klas:")
    for name, cnt in stats.items():
        print(f"  - {name:10s}: {cnt} zdjęć")
    print("==========================================")


if __name__ == "__main__":
    main()
