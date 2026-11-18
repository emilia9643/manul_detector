import os
import sys
import warnings
from PIL import Image
from ultralytics import YOLO

warnings.filterwarnings("ignore")

input_dir = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/cropped"
debug_dir = sys.argv[3] if len(sys.argv) > 3 else "data/debug"

model = YOLO("yolov8n.pt")
manul_classes = [15, 16, 21]
extensions = (".jpg", ".jpeg", ".png", ".webp")

image_files = []
for root, _, files in os.walk(input_dir):
    for file in sorted(files):
        if file.lower().endswith(extensions):
            image_files.append(os.path.join(root, file))

total = len(image_files)
success = 0
no_detection = 0
multiple_animals = 0

for path in image_files:
    rel_path = os.path.relpath(path, input_dir)
    results = model(path, classes=manul_classes, conf=0.4, verbose=False)
    result = results[0]
    boxes = result.boxes

    if len(boxes) == 1:
        x1, y1, x2, y2 = boxes.xyxy[0].tolist()
        try:
            with Image.open(path) as img:
                img_rgb = img.convert("RGB")
                w, h = img_rgb.size
                bw, bh = x2 - x1, y2 - y1
                cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                side = min(max(bw, bh) * 1.16, min(w, h))
                half = side / 2.0
                c_x1 = max(0, min(w - side, cx - half))
                c_y1 = max(0, min(h - side, cy - half))
                cropped = img_rgb.crop((int(c_x1), int(c_y1), int(c_x1 + side), int(c_y1 + side)))
                resized = cropped.resize((224, 224), Image.Resampling.LANCZOS)
                out_path = os.path.join(output_dir, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                resized.save(out_path, quality=95)
            success += 1
        except Exception:
            no_detection += 1
    else:
        if len(boxes) == 0:
            no_detection += 1
        else:
            multiple_animals += 1
        debug_path = os.path.join(debug_dir, rel_path)
        os.makedirs(os.path.dirname(debug_path), exist_ok=True)
        result.save(filename=debug_path)

print(f"Wszystkie zdjęcia: {total}")
print(f"Pomyślnie wycięto: {success}")
print(f"Odrzucono (brak manula): {no_detection}")
print(f"Odrzucono (>1 zwierzę): {multiple_animals}")
print(f"Folder wyciętych: {output_dir}")
print(f"Folder debug: {debug_dir}")
