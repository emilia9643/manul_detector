import os
import time
from ultralytics import YOLO
from PIL import Image

INPUT_DIR = "raw_bol"
CROPPED_DIR = "cropped_bol"
DEBUG_DIR = "debug"

CONF_THRESHOLD = 0.4
MARGIN = 0.05
TARGET_SIZE = (224, 224)

model = YOLO("yolov8n.pt")

valid_extensions = (".jpg", ".jpeg", ".png", ".webp")
image_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(valid_extensions)]


print(f"found {len(image_files)} inputs")
# start_time = time.time()

for filename in image_files:
    img_path = os.path.join(INPUT_DIR, filename)
    # 15,16,21 == cat/dog/bear(in some cases maybe x3)
    results = model(img_path, classes=[15, 16, 21], conf=CONF_THRESHOLD, verbose=False)
    result = results[0]
    boxes = result.boxes
    debug_path = os.path.join(DEBUG_DIR, f"debug_box_{filename}")
    result.save(filename=debug_path)

    if len(boxes) == 0:
        print(f"[POMINIĘTO] {filename} -> YOLO nie znalazło manula na zdjęciu.")
        continue
    elif len(boxes) > 1:
        print(f"[POMINIĘTO] {filename} -> Wykryto więcej niż 1 zwierzę ({len(boxes)}). Sprawdź w '{DEBUG_DIR}'.")
        continue

    # 4. Mamy dokładnie 1 manula! Pobieramy współrzędne ramki
    x1, y1, x2, y2 = boxes.xyxy[0].tolist()
    conf = boxes.conf[0].item()
    cls_id = int(boxes.cls[0].item())
    cls_name = model.names[cls_id]

    img = Image.open(img_path).convert("RGB")
    img_w, img_h = img.size

    box_w = x2 - x1
    box_h = y2 - y1
    x1_m = max(0, int(x1 - box_w * MARGIN))
    y1_m = max(0, int(y1 - box_h * MARGIN))
    x2_m = min(img_w, int(x2 + box_w * MARGIN))
    y2_m = min(img_h, int(y2 + box_h * MARGIN))
    cropped_img = img.crop((x1_m, y1_m, x2_m, y2_m))
    cropped_img = cropped_img.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    out_path = os.path.join(CROPPED_DIR, filename)
    cropped_img.save(out_path, quality=95)

    print(f"[SUKCES]    {filename} -> Wycięto! (rozpoznano jako: '{cls_name}', pewność: {conf:.0%})")

# elapsed = time.time() - start_time
# print(f"\nGotowe! Przetworzono {len(image_files)} zdjęć w {elapsed:.2f} s.")
print(f"-> Sprawdź ramki detekcji w folderze: '{DEBUG_DIR}'")
print(f"-> Sprawdź wycięte manule w folderze: '{CROPPED_DIR}'")