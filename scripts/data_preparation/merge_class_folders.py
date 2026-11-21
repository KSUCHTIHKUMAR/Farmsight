import argparse
import shutil
from collections import defaultdict
from pathlib import Path

SPLITS = ("train", "val", "validation", "test")
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp"}

# Stray files (non-PlantVillage names). Moved to <root>/_excluded, not trained on.
EXCLUDE = {"2700323949_95aa2eaa01_o", "CG1"}

# Official PlantVillage class sizes, used only to double-check the result.
EXPECTED = {
    "Potato___Early_blight": 1000, "Potato___Late_blight": 1000, "Potato___healthy": 152,
    "Tomato___Bacterial_spot": 2127, "Tomato___Early_blight": 1000, "Tomato___Late_blight": 1909,
    "Tomato___Leaf_Mold": 952, "Tomato___Septoria_leaf_spot": 1771, "Tomato___Spider_mites": 1676,
    "Tomato___Target_Spot": 1404, "Tomato___Yellow_Leaf_Curl_Virus": 5357,
    "Tomato___Mosaic_virus": 373, "Tomato___healthy": 1591,
}


def target_for(folder_name):
    if folder_name in EXPECTED:
        return folder_name
    crop, _, suffix = folder_name.partition("___")
    crop = crop.lower()
    if suffix in EXCLUDE:
        return "_excluded"
    c = suffix.upper()
    disease = None
    if crop == "potato":
        disease = {"RS_EARLY.B": "Early_blight", "RS_LB": "Late_blight", "RS_HL": "healthy"}.get(c)
    elif crop == "tomato":
        if c.startswith("GHLB") or c == "RS_LATE.B":
            disease = "Late_blight"
        elif c == "RS_ERLY.B":
            disease = "Early_blight"
        elif c in ("GCREC_BACT.SP", "UF.GRC_BS_LAB_LEAF"):
            disease = "Bacterial_spot"
        elif c == "CRNL_L.MOLD":
            disease = "Leaf_Mold"
        elif c in ("JR_SEPT.L.S", "MATT.S_CG", "KELLER.ST_CG"):
            disease = "Septoria_leaf_spot"
        elif c == "COM.G_SPM_FL":
            disease = "Spider_mites"
        elif c == "COM.G_TGS_FL":
            disease = "Target_Spot"
        elif "YLCV" in c:
            disease = "Yellow_Leaf_Curl_Virus"
        elif c == "PSU_CG":
            disease = "Mosaic_virus"
        elif c == "RS_HL" or c.startswith("GH_HL"):
            disease = "healthy"
    return f"{crop.capitalize()}___{disease}" if disease else None


def images_in(folder):
    return [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXT]


def scan(root):
    moves, unmapped = [], []
    totals = defaultdict(lambda: defaultdict(int))
    for split in SPLITS:
        split_dir = root / split
        if not split_dir.is_dir():
            continue
        for d in sorted(x for x in split_dir.iterdir() if x.is_dir() and "___" in x.name):
            tgt = target_for(d.name)
            n = len(images_in(d))
            if tgt is None:
                unmapped.append((split, d.name, n))
                continue
            totals[tgt][split] += n
            if tgt != d.name:
                moves.append((split, d, tgt))
    return moves, unmapped, totals


def print_summary(moves, unmapped, totals):
    splits_present = [s for s in SPLITS if any(s in v for v in totals.values())]
    print(f"\n{'class folder':34s}" + "".join(f"{s:>12s}" for s in splits_present) + f"{'total':>9s}{'expected':>10s}  check")
    print("-" * (34 + 12 * len(splits_present) + 27))
    for cls in sorted(totals):
        counts = totals[cls]
        total = sum(counts.values())
        exp = EXPECTED.get(cls)
        status = "" if exp is None else ("OK" if total == exp else f"diff {total - exp:+d}")
        print(f"{cls:34s}" + "".join(f"{counts.get(s, 0):12d}" for s in splits_present)
              + f"{total:9d}{(exp if exp else ''):>10}  {status}")
    n_cls = len([c for c in totals if c != "_excluded"])
    print(f"\nClass folders after merging: {n_cls}   Folders to merge/move: {len(moves)}")
    if unmapped:
        print("\nUNMAPPED folders (left alone) - send these to Claude:")
        for split, name, n in unmapped[:30]:
            print(f"  {split:10s} {name} ({n} files)")


def apply_moves(root, moves):
    for split, src, tgt in moves:
        dest = root / "_excluded" / split if tgt == "_excluded" else root / split / tgt
        dest.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_file():
                target = dest / f.name
                if target.exists():
                    raise FileExistsError(f"Refusing to overwrite {target}")
                shutil.move(str(f), str(target))
        try:
            src.rmdir()
        except OSError:
            print(f"NOTE: {src} not empty after moving images - check by hand.")
    per_split = {}
    for split in SPLITS:
        sd = root / split
        if sd.is_dir():
            per_split[split] = {d.name for d in sd.iterdir() if d.is_dir()}
    if per_split:
        ref = next(iter(per_split.values()))
        for split, classes in per_split.items():
            if classes != ref:
                print(f"WARNING: classes in '{split}' differ from other splits: {sorted(classes ^ ref)}")
    print("\nDone. Class folders per split:", {s: len(c) for s, c in per_split.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="Folder containing train/ validation/ test/")
    ap.add_argument("--apply", action="store_true", help="Actually move files (default: dry run)")
    args = ap.parse_args()
    root = Path(args.root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    moves, unmapped, totals = scan(root)
    if not totals and not unmapped:
        print("No class folders (named like Tomato___something) found.")
        return
    print_summary(moves, unmapped, totals)
    if args.apply:
        apply_moves(root, moves)
    else:
        print("\nDRY RUN only - nothing was moved. Re-run with --apply.")


if __name__ == "__main__":
    main()