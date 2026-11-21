import argparse
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def images(folder):
    return sorted(f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT)


def put(src, dst):
    """Hard-link when possible (instant, no extra disk space); otherwise copy."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main():
    ap = argparse.ArgumentParser(description="Build a PlantVillage + PlantDoc training set with a held-out field test set")
    ap.add_argument("--base", default=r"data\leaf_disease", help="PlantVillage folder (train/validation/test)")
    ap.add_argument("--field", default=r"data\leaf_realworld", help="PlantDoc folder (one subfolder per class)")
    ap.add_argument("--out", default=r"data\leaf_mixed", help="Mixed dataset to create")
    ap.add_argument("--field_test_out", default=r"data\leaf_field_test", help="Held-out field test images")
    ap.add_argument("--repeat", type=int, default=5, help="How many times field training images are repeated")
    ap.add_argument("--test_frac", type=float, default=0.25)
    ap.add_argument("--val_frac", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    base, field = Path(args.base), Path(args.field)
    out, test_out = Path(args.out), Path(args.field_test_out)
    for p in (base, field):
        if not p.is_dir():
            raise FileNotFoundError(p)
    if out.exists() or test_out.exists():
        raise SystemExit(f"{out} or {test_out} already exists. Delete them first to rebuild.")

    # 1) PlantVillage: link train / validation / test as they are
    n_base = defaultdict(int)
    for name, target in (("train", "train"), ("validation", "validation"), ("val", "validation"), ("test", "test")):
        split_dir = base / name
        if not split_dir.is_dir():
            continue
        for cls_dir in sorted(d for d in split_dir.iterdir() if d.is_dir()):
            for f in images(cls_dir):
                put(f, out / target / cls_dir.name / f.name)
                n_base[target] += 1

    # 2) PlantDoc: stratified split into field-train / field-val / field-test
    rng = random.Random(args.seed)
    rows = []
    for cls_dir in sorted(d for d in field.iterdir() if d.is_dir()):
        files = images(cls_dir)
        rng.shuffle(files)
        n = len(files)
        if n >= 4:
            n_test = max(1, round(n * args.test_frac))
            n_val = max(1, round(n * args.val_frac))
        else:
            n_test = n_val = 0  # too small to split: all goes to training
        test, val, train = files[:n_test], files[n_test:n_test + n_val], files[n_test + n_val:]
        for f in test:
            put(f, test_out / cls_dir.name / f.name)
        for f in val:
            put(f, out / "validation" / cls_dir.name / f"field_{f.name}")
        for k in range(args.repeat):
            for f in train:
                put(f, out / "train" / cls_dir.name / f"field{k}_{f.name}")
        rows.append((cls_dir.name, len(train), len(val), len(test)))

    print(f"\n{'field class':36s}{'train':>7s}{'val':>6s}{'test':>6s}")
    print("-" * 55)
    for name, a, b, c in rows:
        print(f"{name:36s}{a:7d}{b:6d}{c:6d}")
    ta, tb, tc = (sum(r[i] for r in rows) for i in (1, 2, 3))
    print(f"{'TOTAL':36s}{ta:7d}{tb:6d}{tc:6d}")
    print(f"\nPlantVillage linked: {dict(n_base)}")
    print(f"Field training images are repeated x{args.repeat} (augmentation makes each repeat different).")
    print(f"\nMixed dataset:   {out.resolve()}")
    print(f"Field test set:  {test_out.resolve()}   <- the honest real-world number; never train on it")


if __name__ == "__main__":
    main()