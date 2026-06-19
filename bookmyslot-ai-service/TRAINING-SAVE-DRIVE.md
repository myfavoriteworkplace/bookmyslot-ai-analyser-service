# DENTEX YOLOv8 Training Workflow — Google Drive Persistent Version

> This is the **Google Drive–persistent variant** of the training workflow.
> The base guide is [`TRAINING.md`](./TRAINING.md).
> Read the deviations section below before following any steps.

---

## Deviations from TRAINING.md

Every difference from the base `TRAINING.md` guide is listed here. Steps not mentioned are identical.

---

### Step 7 — YOLO folder structure location

**TRAINING.md (local Colab):**
```
/content/dentex_yolo/images/train
/content/dentex_yolo/images/val
/content/dentex_yolo/labels/train
/content/dentex_yolo/labels/val
```
These paths are lost when Colab restarts.

**This guide (Google Drive):**
```
/content/drive/MyDrive/dentex_project/yolo/images/train
/content/drive/MyDrive/dentex_project/yolo/images/val
/content/drive/MyDrive/dentex_project/yolo/labels/train
/content/drive/MyDrive/dentex_project/yolo/labels/val
```
Persisted permanently in Google Drive.

Full Drive structure created:
```
dentex_project/
├── yolo/
│   ├── images/
│   │   ├── train/
│   │   └── val/
│   └── labels/
│       ├── train/
│       └── val/
└── models/
    └── dentex_training/
        └── weights/
            └── best.pt   ← saved here automatically by training
```

---

### Step 8 — Training images destination

**TRAINING.md:** copies to `/content/dentex_yolo/images/train/`

**This guide:** copies to `/content/drive/MyDrive/dentex_project/yolo/images/train/`

---

### Step 9 — Label file paths

**TRAINING.md:**
- Reads image from `/content/dentex_yolo/images/train/`
- Writes labels to `/content/dentex_yolo/labels/train/`

**This guide:**
- Reads image from `/content/drive/MyDrive/dentex_project/yolo/images/train/`
- Writes labels to `/content/drive/MyDrive/dentex_project/yolo/labels/train/`

---

### Step 11 — YOLO YAML location and class names

**TRAINING.md:** YAML written to `/content/dentex.yaml` (local, lost on restart)

Class names:
```yaml
names:
  0: "1"
  1: "2"
  2: "3"
  3: "4"
```

**This guide:** YAML written to `/content/drive/MyDrive/dentex_project/dentex.yaml` (persisted)

Class names updated to human-readable labels:
```yaml
names: [ 'Finding Type 1', 'Finding Type 2', 'Finding Type 3', 'Finding Type 4' ]
```

> These names match the `CLASS_MAPPING` in `app/model.py` exactly so training labels and API responses are consistent.

---

### Step 13 — Training output destination

**TRAINING.md:** Saves training output to Colab local storage (lost on restart):
```python
model.train(
    data="/content/dentex.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    cache=True,
    workers=2
)
```
Output goes to: `/content/runs/detect/train/weights/best.pt`

**This guide:** Saves directly to Drive using `project` and `name` params:
```python
model.train(
    data="/content/drive/MyDrive/dentex_project/dentex.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    cache=True,
    workers=2,
    project="/content/drive/MyDrive/dentex_project/models",
    name="dentex_training"
)
```
Output goes to: `/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt`

---

### Step 14 — Model location after training

**TRAINING.md:**
```
/content/runs/detect/train/weights/best.pt
```

**This guide:**
```
/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt
```

---

### Step 17 — Saving the model

**TRAINING.md:** requires a manual copy step after training:
```python
!cp /content/runs/detect/train/weights/best.pt \
    /content/drive/MyDrive/bookmyslot-best.pt
```

**This guide:** model is **already in Drive** after training — no copy needed. Training writes directly to:
```
/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt
```

To use it with the FastAPI service, share the file from Google Drive and set:
```
MODEL_DOWNLOAD_URL = https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing
```

---

## Full Workflow

### 1. Install Dependencies

```python
!pip install ultralytics datasets huggingface_hub opencv-python pillow matplotlib tqdm
```

Verify:

```python
import ultralytics
print(ultralytics.__version__)
```

---

### 2. Enable GPU

Colab: **Runtime → Change runtime type → GPU**

```bash
!nvidia-smi
```

---

### 3. Mount Google Drive

> **New step not in TRAINING.md** — must be done before anything else.

```python
from google.colab import drive
drive.mount('/content/drive')
```

---

### 4. Authenticate HuggingFace

```python
from huggingface_hub import login
login("YOUR_HF_TOKEN")
```

---

### 5. Download DENTEX Dataset

```python
from huggingface_hub import snapshot_download

dataset_path = snapshot_download(
    repo_id="ibrahimhamamci/DENTEX",
    repo_type="dataset"
)
print(dataset_path)
```

---

### 6. Extract Dataset

```python
import zipfile

dataset_root = f"{dataset_path}/DENTEX"

with zipfile.ZipFile(f"{dataset_root}/training_data.zip") as z:
    z.extractall("/content/dentex_train")

with zipfile.ZipFile(f"{dataset_root}/validation_data.zip") as z:
    z.extractall("/content/dentex_val")
```

---

### 7. Load Training Annotations

```python
from datasets import load_dataset

train_ann = load_dataset(
    "json",
    data_files="/content/dentex_train/training_data/quadrant-enumeration-disease/train_quadrant_enumeration_disease.json"
)
```

---

### 8. Create YOLO Folder Structure in Google Drive

```python
import os

folders = [
    "/content/drive/MyDrive/dentex_project/yolo/images/train",
    "/content/drive/MyDrive/dentex_project/yolo/images/val",
    "/content/drive/MyDrive/dentex_project/yolo/labels/train",
    "/content/drive/MyDrive/dentex_project/yolo/labels/val"
]

for folder in folders:
    os.makedirs(folder, exist_ok=True)
```

---

### 9. Copy Training Images to Drive

```python
import shutil
from tqdm import tqdm

image_source = "/content/dentex_train/training_data/quadrant-enumeration-disease/xrays"

for item in tqdm(train_ann["train"]):
    filename = item["images"][0]["file_name"]
    shutil.copy(
        f"{image_source}/{filename}",
        f"/content/drive/MyDrive/dentex_project/yolo/images/train/{filename}"
    )
```

---

### 10. Convert COCO Bounding Boxes to YOLO Format (Write to Drive)

```python
from PIL import Image

def convert_bbox(bbox, w, h):
    x, y, bw, bh = bbox
    return (
        (x + bw / 2) / w,
        (y + bh / 2) / h,
        bw / w,
        bh / h
    )

for item in train_ann["train"]:
    image = item["images"][0]
    filename = image["file_name"]

    img = Image.open(f"/content/drive/MyDrive/dentex_project/yolo/images/train/{filename}")
    width, height = img.size

    with open(
        f"/content/drive/MyDrive/dentex_project/yolo/labels/train/{filename.replace('.png', '.txt')}",
        "w"
    ) as f:
        for ann in item["annotations"]:
            cls = ann["category_id_1"]
            x, y, w, h = convert_bbox(ann["bbox"], width, height)
            f.write(f"{cls} {x} {y} {w} {h}\n")
```

---

### 11. Validation Dataset

```python
val_ds = load_dataset(
    "json",
    data_files=f"{dataset_root}/validation_triple.json"
)
```

Validation images source:
```
/content/dentex_val/validation_data/quadrant_enumeration_disease/xrays
```

Copy to `/content/drive/MyDrive/dentex_project/yolo/images/val` and generate labels using the same `convert_bbox` function, writing to `/content/drive/MyDrive/dentex_project/yolo/labels/val`.

---

### 12. Create YOLO YAML in Drive

```python
%%writefile /content/drive/MyDrive/dentex_project/dentex.yaml
train: /content/drive/MyDrive/dentex_project/yolo/images/train
val: /content/drive/MyDrive/dentex_project/yolo/images/val

nc: 4
names: [ 'Finding Type 1', 'Finding Type 2', 'Finding Type 3', 'Finding Type 4' ]
```

---

### 13. Verify Dataset

```python
import os

print("Train images:", len(os.listdir("/content/drive/MyDrive/dentex_project/yolo/images/train")))
print("Train labels:", len(os.listdir("/content/drive/MyDrive/dentex_project/yolo/labels/train")))
print("Val images:",   len(os.listdir("/content/drive/MyDrive/dentex_project/yolo/images/val")))
print("Val labels:",   len(os.listdir("/content/drive/MyDrive/dentex_project/yolo/labels/val")))
```

---

### 14. Train YOLOv8 (Output Saved to Drive)

```python
from ultralytics import YOLO

model = YOLO("yolov8s.pt")

model.train(
    data="/content/drive/MyDrive/dentex_project/dentex.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    device=0,
    cache=True,
    workers=2,
    project="/content/drive/MyDrive/dentex_project/models",
    name="dentex_training"
)
```

---

### 15. Locate Model

Training saves directly to Drive:

```
/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt
```

Verify:

```bash
!ls /content/drive/MyDrive/dentex_project/models/dentex_training/weights/
```

---

### 16. Validate Model

```python
model = YOLO("/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt")
metrics = model.val()
```

---

### 17. Test Prediction

```python
results = model.predict(
    source="/content/drive/MyDrive/dentex_project/yolo/images/val/sample.png",
    conf=0.25,
    save=True
)
results[0].show()
```

---

### 18. Model is Already Saved — No Copy Needed

The model is persisted at:
```
/content/drive/MyDrive/dentex_project/models/dentex_training/weights/best.pt
```

To connect it to the FastAPI service:
1. Right-click the file in Google Drive → Share → "Anyone with the link" → Viewer
2. Copy the share link
3. Set it as `MODEL_DOWNLOAD_URL` on Render:
   ```
   MODEL_DOWNLOAD_URL = https://drive.google.com/file/d/YOUR_FILE_ID/view?usp=sharing
   ```

The service auto-downloads `best.pt` on first boot.

---

## Achievement Summary

| Step | Status |
|---|---|
| Dataset download | ✅ |
| Annotation conversion | ✅ |
| YOLO structure creation (in Drive) | ✅ |
| YOLOv8 training (output to Drive) | ✅ |
| Inference testing | ✅ |
| Persistence in Google Drive | ✅ |

## Production Architecture

```
React App
    |
Node Backend
    |
FastAPI AI Service (bookmyslot-ai-service)
    |
YOLOv8 best.pt  ←  downloaded from Google Drive via MODEL_DOWNLOAD_URL
```
