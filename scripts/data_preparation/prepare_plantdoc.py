import argparse
import re
import shutil
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}

# PlantDoc class folder name (lowercase, spaces) -> our class folder name
MAP = {
    "tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "tomato early blight leaf": "Tomato___Early_blight",
    "tomato leaf late blight": "Tomato___Late_blight",
    "tomato mold leaf": "Tomato___Leaf_Mold",
    "tomato leaf mosaic virus": "Tomato___Mosaic_virus",
    "tomato septoria leaf spot": "Tomato___Septoria_leaf_spot",
    "tomato two spotted spider mites leaf": "Tomato___Spider_mites",
    "tomato leaf yellow virus": "Tomato___Yellow_Leaf_Curl_Virus",
    "tomato leaf": "Tomato___healthy",
    "potato leaf early blight": "Potato___Early_blight",
    "potato leaf late blight": "Potato___Late_blight",
    "potato leaf": "Potato___healthy",
}


def normalize(name):
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", name)).strip().lower()


def main():
    ap = argparse.ArgumentParser(description="Copy matching PlantDoc classes into a real-world holdout folder")
    ap.add_argument("--src", required=True, help="Unzipped PlantDoc folder")
    ap.add_argument("--out", required=True, help="Holdout folder to create, e.g. data\\leaf_realworld")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    if not src.is_dir():
        raise FileNotFoundError(src)

    counts, matched = {}, 0
    for d in sorted(p for p in src.rglob("*") if p.is_dir()):
        cls = MAP.get(normalize(d.name))
        if cls is None:
            continue
        matched += 1
        dest = out / cls
        dest.mkdir(parents=True, exist_ok=True)
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() in IMG_EXT:
                target = dest / f"{d.parent.name}_{f.name}"  # parent = train/test, avoids name clashes
                if not target.exists():
                    shutil.copy2(f, target)
                    counts[cls] = counts.get(cls, 0) + 1

    if matched and not counts:
        print("Everything was already copied (nothing new to add).")
        return
    if not counts:
        print("No matching class folders found. Run  dir <your PlantDoc folder> -Recurse -Directory  and send it to Claude.")
        return
    print(f"\n{'class folder':36s}{'images':>8s}")
    print("-" * 44)
    for cls in sorted(counts):
        print(f"{cls:36s}{counts[cls]:8d}")
    print(f"\nTotal: {sum(counts.values())} images in {len(counts)} classes -> {out.resolve()}")
    missing = sorted({v for v in MAP.values()} - set(counts))
    if missing:
        print("Classes with no PlantDoc images:", ", ".join(missing))


if __name__ == "__main__":
    main()