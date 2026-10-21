"""
Moduł automatycznego kadrowania (Auto-Cropping) osobników manula przy użyciu YOLOv8.
Zaprojektowany do wycinania sylwetki/twarzy zwierzęcia w celu eliminacji zjawiska
Shortcut Learning (uczenia się tła wybiegu zamiast cech anatomicznych kota).

Wspiera:
- Strukturę folderów klasowych: data/raw/<klasa>/ -> data/cropped/<klasa>/
- Kwadratowe kadrowanie z zachowaniem proporcji (brak zniekształceń proporcji ciała/pyska)
- Zapis ramek diagnostycznych w data/debug/<klasa>/
- Statystyki odrzuceń (brak zwierzęcia vs wiele zwierząt)
"""
import os
import argparse
import time
from ultralytics import YOLO
from PIL import Image

VALID_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")
# Klasy COCO: 15 (cat), 16 (dog), 21 (bear) - manul w zimowym futrze bywa klasyfikowany jako niedźwiedź/pies
TARGET_CLASSES = [15, 16, 21]


def square_crop_coordinates(box, img_w, img_h, margin=0.08):
    """
    Oblicza współrzędne kadrowania kwadratowego ze środkiem w wykrytym obiekcie.
    Gwarantuje brak zniekształceń proporcji (aspect ratio) bez konieczności czarnych pasów.
    """
    x1, y1, x2, y2 = box
    box_w = x2 - x1
    box_h = y2 - y1
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    # Rozmiar kwadratu z uwzględnieniem marginesu
    square_size = max(box_w, box_h) * (1.0 + 2.0 * margin)

    # Ograniczenie do maksymalnego możliwego wymiaru zdjęcia
    max_possible = min(img_w, img_h)
    if square_size > max_possible:
        square_size = max_possible

    half = square_size / 2.0

    # Przesunięcie środka, jeśli kwadrat wystaje poza krawędzie
    crop_x1 = cx - half
    crop_y1 = cy - half

    if crop_x1 < 0:
        crop_x1 = 0
    elif crop_x1 + square_size > img_w:
        crop_x1 = img_w - square_size

    if crop_y1 < 0:
        crop_y1 = 0
    elif crop_y1 + square_size > img_h:
        crop_y1 = img_h - square_size

    crop_x2 = crop_x1 + square_size
    crop_y2 = crop_y1 + square_size

    return int(round(crop_x1)), int(round(crop_y1)), int(round(crop_x2)), int(round(crop_y2))


def process_dataset(
    input_dir="data/raw",
    output_dir="data/cropped",
    debug_dir="data/debug",
    model_path="yolov8n.pt",
    conf_threshold=0.4,
    margin=0.08,
    target_size=(224, 224),
    save_debug=True,
):
    print("=== PIPELINE KADROWANIA (YOLOv8 AUTO-CROPPING) ===")
    print(f"Model: {model_path} | Próg pewności: {conf_threshold} | Margines: {margin:.0%}")
    print(f"Katalog źródłowy: '{input_dir}' -> Docelowy: '{output_dir}'")

    if not os.path.exists(model_path):
        print(f"[INFO] Pobieranie wag modelu {model_path}...")
    model = YOLO(model_path)

    # Sprawdzenie czy input_dir zawiera podfoldery (struktura klasowa)
    subdirs = [
        d for d in os.listdir(input_dir)
        if os.path.isdir(os.path.join(input_dir, d)) and not d.startswith(".")
    ]

    # Jeśli brak podkatalogów, traktujemy input_dir jako pojedynczą klasę
    if not subdirs:
        classes = ["."]
    else:
        classes = sorted(subdirs)

    total_stats = {
        "total": 0,
        "success": 0,
        "no_detection": 0,
        "multiple_animals": 0,
    }

    start_time = time.time()

    for cls in classes:
        cls_input_dir = os.path.join(input_dir, cls) if cls != "." else input_dir
        cls_output_dir = os.path.join(output_dir, cls) if cls != "." else output_dir
        cls_debug_dir = os.path.join(debug_dir, cls) if cls != "." else debug_dir

        os.makedirs(cls_output_dir, exist_ok=True)
        if save_debug:
            os.makedirs(cls_debug_dir, exist_ok=True)

        image_files = sorted([
            f for f in os.listdir(cls_input_dir)
            if f.lower().endswith(VALID_EXTENSIONS)
        ])

        print(f"\n--- Przetwarzanie klasy: {cls.upper()} ({len(image_files)} zdjęć) ---")

        cls_success = 0
        cls_no_det = 0
        cls_multi = 0

        for idx, filename in enumerate(image_files, start=1):
            img_path = os.path.join(cls_input_dir, filename)
            out_path = os.path.join(cls_output_dir, filename)

            # Pomijamy, jeśli zdjęcie zostało już wcześniej wycięte
            if os.path.exists(out_path):
                cls_success += 1
                continue

            results = model(
                img_path,
                classes=TARGET_CLASSES,
                conf=conf_threshold,
                verbose=False,
            )
            result = results[0]
            boxes = result.boxes

            # Zapis podglądu detekcji
            if save_debug:
                debug_path = os.path.join(cls_debug_dir, f"box_{filename}")
                result.save(filename=debug_path)

            if len(boxes) == 0:
                cls_no_det += 1
                continue
            elif len(boxes) > 1:
                cls_multi += 1
                continue

            # Dokładnie 1 manul wykryty
            x1, y1, x2, y2 = boxes.xyxy[0].tolist()
            conf = boxes.conf[0].item()
            cls_name = model.names[int(boxes.cls[0].item())]

            try:
                with Image.open(img_path) as img:
                    img_rgb = img.convert("RGB")
                    img_w, img_h = img_rgb.size

                    crop_x1, crop_y1, crop_x2, crop_y2 = square_crop_coordinates(
                        (x1, y1, x2, y2), img_w, img_h, margin=margin
                    )

                    cropped = img_rgb.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                    resized = cropped.resize(target_size, Image.Resampling.LANCZOS)
                    resized.save(out_path, quality=95)

                cls_success += 1
                if idx % 20 == 0 or idx == len(image_files):
                    print(f"  [{idx:03d}/{len(image_files)}] Postęp w {cls}: {cls_success} wyciętych...")
            except Exception as e:
                print(f"  [BŁĄD] Plik {filename}: {e}")

        total_stats["total"] += len(image_files)
        total_stats["success"] += cls_success
        total_stats["no_detection"] += cls_no_det
        total_stats["multiple_animals"] += cls_multi

        print(f"Podsumowanie {cls}: {cls_success}/{len(image_files)} wyciętych "
              f"| Odrzucono: {cls_no_det} (brak) / {cls_multi} (>1 zwierzę)")

    elapsed = time.time() - start_time
    print("\n==========================================")
    print("ZAKOŃCZONO PROCES KADROWANIA")
    print(f"Czas trwania: {elapsed:.1f} s")
    print(f"Łącznie zdjęć na wejściu: {total_stats['total']}")
    print(f"Pomyślnie wycięto:        {total_stats['success']} ({total_stats['success']/max(1, total_stats['total']):.1%})")
    print(f"Odrzucono (brak detekcji): {total_stats['no_detection']}")
    print(f"Odrzucono (>1 zwierzę):    {total_stats['multiple_animals']}")
    print(f"Wycięte zbiory znajdują się w: '{output_dir}'")
    print("==========================================")


def main():
    parser = argparse.ArgumentParser(description="Kadrowanie zdjęć manuli przy użyciu YOLOv8.")
    parser.add_argument("--input", default="data/raw", help="Folder ze zdjęciami (domyślnie: data/raw)")
    parser.add_argument("--output", default="data/cropped", help="Folder docelowy (domyślnie: data/cropped)")
    parser.add_argument("--debug", default="data/debug", help="Folder podglądów (domyślnie: data/debug)")
    parser.add_argument("--conf", type=float, default=0.4, help="Próg pewności YOLO (domyślnie: 0.4)")
    parser.add_argument("--margin", type=float, default=0.08, help="Margines wokół ramki (domyślnie: 0.08)")
    parser.add_argument("--size", type=int, default=224, help="Rozmiar wyjściowy (domyślnie: 224)")
    parser.add_argument("--no-debug", action="store_true", help="Nie zapisuj podglądów detekcji")

    args = parser.parse_args()

    process_dataset(
        input_dir=args.input,
        output_dir=args.output,
        debug_dir=args.debug,
        conf_threshold=args.conf,
        margin=args.margin,
        target_size=(args.size, args.size),
        save_debug=not args.no_debug,
    )


if __name__ == "__main__":
    main()
