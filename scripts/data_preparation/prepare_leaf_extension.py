"""Prepare a leakage-checked extension of the existing seven-crop leaf dataset."""

import argparse
import hashlib
import json
import os
import random
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import torch
from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
TOM_ROOT = (
    ROOT
    / "01 - Tomato_Onion_Mazie_ Pests_Disease Dataset"
    / "Tomato_Onion_Mazie_ Pests_Disease Dataset"
    / "CATEGORY A"
    / "CATA-English"
)
JUTE_ROOT = (
    ROOT
    / "06 - Jute Leaf Disease Detection"
    / "Jute Leaf Disease Detection"
)
BASE_DATA = ROOT / "data" / "leaf_all_crops_v5"
BASE_CHECKPOINT = ROOT / "runs" / "leaf_7crop_candidate_v7" / "model.pt"
OUTPUT = ROOT / "data" / "leaf_all_crops_v6"
UNKNOWN_CROPS = {
    "Banana", "Carrot", "Guava", "Jujube", "Orange", "Pomegranate", "Strawberry",
}
UNKNOWN_LABEL = "Unknown___leaf"

TOM_CLASS_LABELS = {
    "maize_diseases/Abiotic_disease-D": "Maize___Abiotic_disease",
    "maize_diseases/Curvularia-D": "Maize___Curvularia",
    "maize_diseases/Healthy_leaf": "Maize___healthy",
    "maize_diseases/Helminthosporiosis-D": "Maize___Helminthosporiosis",
    "maize_diseases/Rust-D": "Maize___Rust",
    "maize_diseases/Stripe-D": "Maize___Stripe",
    "maize_diseases/Virosis-D": "Maize___Virosis",
    "maize_pests/Aphids-P": "Maize___Aphids",
    "maize_pests/Spodoptera_frugiperda-P": "Maize___Spodoptera_frugiperda",
    "onion_diseases/Alternaria_D": "Onion___Alternaria",
    "onion_diseases/Fusarium-D": "Onion___Fusarium",
    "onion_diseases/Healthy_leaf": "Onion___healthy",
    "onion_diseases/Virosis-D": "Onion___Virosis",
    "onion_pests/Caterpillar-P": "Onion___Caterpillar",
    "tomato_diseases/alternaria_d": "Tomato___Alternaria",
    "tomato_diseases/alternaria_mite_d": "Tomato___Alternaria_Mite",
    "tomato_diseases/Bacterial_floundering_d": "Tomato___Bacterial_floundering",
    "tomato_diseases/exces_nitrogen_d": "Tomato___Excess_nitrogen",
    "tomato_diseases/fusarium_d": "Tomato___Fusarium",
    "tomato_diseases/healthy_leaf": "Tomato___healthy",
    "tomato_diseases/Mite_d": "Tomato___Mite",
    "tomato_diseases/tomato_late_blight_d": "Tomato___Late_blight",
    "tomato_diseases/virosis_d": "Tomato___Virosis",
}
JUTE_CLASS_LABELS = {
    "Cercospora Leaf Spot": "Jute___Cercospora_Leaf_Spot",
    "Golden Mosaic": "Jute___Golden_Mosaic",
    "Healthy Leaf": "Jute___healthy",
}
EXCLUDED_TOM_FOLDERS = {
    "maize_pests_activities": "activity/augmented imagery, not a disease class",
    "onion_diseases/Bulb_blight-D": "bulb imagery, not leaf imagery",
    "tomato_diseases/healthy_fruit": "fruit imagery, not leaf imagery",
    "tomato_diseases/Blossom_end_rot_d": "fruit imagery, not leaf imagery",
    "tomato_diseases/sunburn_d": "fruit imagery, not leaf imagery",
    "tomato_pests": "sampled examples show tomato fruit rather than leaves",
}


def image_files(folder):
    return sorted(
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def image_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for block in iter(lambda: image_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_image(path):
    with Image.open(path) as image:
        image.seek(0)
        size = image.size
        mode = image.mode
        image.verify()
    return size, mode, image_digest(path)


def source_family(path, source):
    stem = path.stem.lower()
    if source == "tom":
        match = re.match(r"(\d+_\d+)", stem)
        if match:
            return f"tom:{match.group(1)}"
    normalized = re.sub(r"[\s_-]+", "", stem)
    return f"{source}:{normalized}"


def collect_external_records(tom_root, jute_root):
    records, excluded = [], Counter()
    if not tom_root.is_dir():
        raise FileNotFoundError(f"TOM English-label directory not found: {tom_root}")
    if not jute_root.is_dir():
        raise FileNotFoundError(f"Jute dataset directory not found: {jute_root}")

    for relative, label in TOM_CLASS_LABELS.items():
        folder = tom_root.joinpath(*relative.split("/"))
        if not folder.is_dir():
            raise FileNotFoundError(f"Expected TOM class folder not found: {folder}")
        for path in image_files(folder):
            records.append({
                "path": path,
                "label": label,
                "source": "tom",
                "family": source_family(path, "tom"),
            })

    for folder_name, label in JUTE_CLASS_LABELS.items():
        folder = jute_root / folder_name
        if not folder.is_dir():
            raise FileNotFoundError(f"Expected Jute class folder not found: {folder}")
        for path in image_files(folder):
            records.append({
                "path": path,
                "label": label,
                "source": "jute",
                "family": source_family(path, "jute"),
            })

    for folder_name, reason in EXCLUDED_TOM_FOLDERS.items():
        folders = [tom_root / folder_name] if "/" not in folder_name else [
            tom_root.joinpath(*folder_name.split("/"))
        ]
        for folder in folders:
            if folder.is_dir():
                excluded[f"{folder_name}: {reason}"] += len(image_files(folder))

    category_a = tom_root.parent
    dataset_root = category_a.parent
    french_root = category_a / "CATA-French"
    category_b = dataset_root / "CATEGORY B"
    inventory = {
        "tom_category_a_english_images": len(image_files(tom_root)),
        "tom_category_a_french_images": len(image_files(french_root))
        if french_root.is_dir() else 0,
        "tom_category_b_images": len(image_files(category_b))
        if category_b.is_dir() else 0,
        "jute_images": sum(
            len(image_files(jute_root / folder))
            for folder in JUTE_CLASS_LABELS
        ),
    }
    return records, excluded, inventory


def _read_base_records(base_root, classes):
    split_names = {
        "train": ("train",),
        "validation": ("val", "validation"),
        "test": ("test",),
    }
    records, errors = [], []
    for output_split, candidates in split_names.items():
        split_root = next(
            (base_root / name for name in candidates if (base_root / name).is_dir()),
            None,
        )
        if split_root is None:
            raise FileNotFoundError(
                f"Missing {output_split} split under {base_root}"
            )
        for folder in sorted(path for path in split_root.iterdir() if path.is_dir()):
            source_label = folder.name
            crop = source_label.split("___", maxsplit=1)[0]
            if source_label in classes:
                label = source_label
            elif crop in UNKNOWN_CROPS:
                label = UNKNOWN_LABEL
            else:
                continue
            for path in image_files(folder):
                try:
                    size, mode, digest = inspect_image(path)
                except (OSError, ValueError, UnidentifiedImageError) as error:
                    errors.append({"path": str(path), "error": str(error)})
                    continue
                records.append({
                    "path": path,
                    "label": label,
                    "source_label": source_label,
                    "split": output_split,
                    "size": size,
                    "mode": mode,
                    "digest": digest,
                })
    return records, errors


def _deduplicate_base(records):
    groups = defaultdict(list)
    for record in records:
        groups[record["digest"]].append(record)
    kept, duplicate_groups, ambiguous_groups = [], 0, 0
    priority = {"test": 0, "validation": 1, "train": 2}
    for items in groups.values():
        if len(items) == 1:
            kept.extend(items)
            continue
        duplicate_groups += 1
        if len({item["label"] for item in items}) > 1:
            ambiguous_groups += 1
            continue
        selected = min(items, key=lambda item: (priority[item["split"]], str(item["path"])))
        kept.append(selected)
    return kept, {
        "duplicate_groups": duplicate_groups,
        "ambiguous_groups": ambiguous_groups,
        "removed_images": len(records) - len(kept),
    }


def _clean_external_records(records, base_digests):
    valid, corrupt, dimensions, modes = [], [], Counter(), Counter()
    for record in records:
        try:
            size, mode, digest = inspect_image(record["path"])
        except (OSError, ValueError, UnidentifiedImageError) as error:
            corrupt.append({"path": str(record["path"]), "error": str(error)})
            continue
        record.update({"size": size, "mode": mode, "digest": digest})
        dimensions[f"{size[0]}x{size[1]}"] += 1
        modes[mode] += 1
        valid.append(record)

    by_digest = defaultdict(list)
    for record in valid:
        by_digest[record["digest"]].append(record)

    retained, duplicate_count, ambiguous_count = [], 0, 0
    base_overlap_count, base_label_conflicts = 0, 0
    for digest, items in by_digest.items():
        if digest in base_digests:
            base_overlap_count += len(items)
            if any(item["label"] not in base_digests[digest] for item in items):
                base_label_conflicts += len(items)
            continue
        if len({item["label"] for item in items}) > 1:
            ambiguous_count += 1
            continue
        duplicate_count += len(items) - 1
        retained.append(min(items, key=lambda item: str(item["path"])))

    by_family = defaultdict(list)
    for record in retained:
        by_family[record["family"]].append(record)
    conflicted_families = {
        family for family, items in by_family.items()
        if len({item["label"] for item in items}) > 1
    }
    family_conflicts = sum(
        len(by_family[family]) for family in conflicted_families
    )
    retained = [
        item for family, items in by_family.items()
        if family not in conflicted_families
        for item in items
    ]
    return retained, {
        "corrupt_images": corrupt,
        "dimensions": dict(dimensions),
        "modes": dict(modes),
        "exact_duplicates_removed": duplicate_count,
        "ambiguous_exact_duplicate_groups_removed": ambiguous_count,
        "exact_overlaps_with_existing_dataset_removed": base_overlap_count,
        "overlap_label_conflicts": base_label_conflicts,
        "source_families_with_conflicting_labels_removed": len(conflicted_families),
        "images_in_conflicting_source_families_removed": family_conflicts,
    }


def split_external_records(records, seed=42):
    by_label_family = defaultdict(lambda: defaultdict(list))
    for record in records:
        by_label_family[record["label"]][record["family"]].append(record)

    assigned = []
    small_classes = {}
    for label, families in sorted(by_label_family.items()):
        units = sorted(families.items())
        random.Random(f"{seed}:{label}").shuffle(units)
        count = len(units)
        if count < 3:
            small_classes[label] = count
            split_sizes = {"train": count, "validation": 0, "test": 0}
        else:
            test_count = max(1, round(count * 0.15))
            validation_count = max(1, round(count * 0.15))
            while test_count + validation_count >= count:
                if test_count >= validation_count:
                    test_count -= 1
                else:
                    validation_count -= 1
            split_sizes = {
                "train": count - validation_count - test_count,
                "validation": validation_count,
                "test": test_count,
            }

        cursor = 0
        for split in ("train", "validation", "test"):
            next_cursor = cursor + split_sizes[split]
            for _, group in units[cursor:next_cursor]:
                assigned.extend({**record, "split": split} for record in group)
            cursor = next_cursor
    return assigned, small_classes


def build_class_mapping(split_counts):
    classes = sorted({
        label
        for class_counts in split_counts.values()
        for label, count in class_counts.items()
        if count
    })
    return classes, {label: index for index, label in enumerate(classes)}


def _link_or_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def prepare_dataset(
    base_root, tom_root, jute_root, checkpoint_path, output_root, seed=42
):
    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty; refusing to overwrite: {output_root}"
        )
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    base_classes = checkpoint.get("classes")
    if not isinstance(base_classes, list) or not base_classes:
        raise ValueError(f"Checkpoint has no class mapping: {checkpoint_path}")

    base_records, base_corrupt = _read_base_records(base_root, base_classes)
    base_records, base_dedup = _deduplicate_base(base_records)
    base_digests = defaultdict(set)
    for record in base_records:
        base_digests[record["digest"]].add(record["label"])

    external_records, excluded, source_inventory = collect_external_records(
        tom_root, jute_root
    )
    external_records, external_report = _clean_external_records(
        external_records, base_digests
    )
    external_records, small_classes = split_external_records(external_records, seed)

    output_root.mkdir(parents=True, exist_ok=True)
    counts = {split: Counter() for split in ("train", "validation", "test")}
    external_counts = {split: Counter() for split in ("train", "validation", "test")}
    for record in base_records:
        destination = output_root / record["split"] / record["label"] / record["path"].name
        _link_or_copy(record["path"], destination)
        counts[record["split"]][record["label"]] += 1

    for record in external_records:
        name = f"{record['digest'][:12]}_{record['path'].name}"
        destination = (
            output_root / record["split"] / record["label"] / name
        )
        _link_or_copy(record["path"], destination)
        counts[record["split"]][record["label"]] += 1
        external_counts[record["split"]][record["label"]] += 1

    split_counts = {
        split: dict(sorted(split_counts.items()))
        for split, split_counts in counts.items()
    }
    classes, class_to_idx = build_class_mapping(split_counts)
    manifest = {
        "base_checkpoint": str(checkpoint_path),
        "base_data": str(base_root),
        "unknown_crop_examples": sorted(UNKNOWN_CROPS),
        "tom_source": str(tom_root),
        "jute_source": str(jute_root),
        "seed": seed,
        "classes": classes,
        "class_to_idx": class_to_idx,
        "split_counts": split_counts,
        "external_split_counts": {
            split: dict(sorted(split_counts.items()))
            for split, split_counts in external_counts.items()
        },
        "base_corrupt_images": base_corrupt,
        "base_duplicate_cleanup": base_dedup,
        "external_scan": external_report,
        "source_inventory": source_inventory,
        "external_classes_without_held_out_examples": small_classes,
        "excluded_tom_folders": dict(excluded),
        "excluded_images_by_reason": dict(sorted(excluded.items())),
    }
    (output_root / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    (output_root / "class_labels.json").write_text(
        json.dumps({"classes": classes, "class_to_idx": class_to_idx}, indent=2),
        encoding="utf-8",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=BASE_DATA)
    parser.add_argument("--tom-root", type=Path, default=TOM_ROOT)
    parser.add_argument("--jute-root", type=Path, default=JUTE_ROOT)
    parser.add_argument("--checkpoint", type=Path, default=BASE_CHECKPOINT)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    manifest = prepare_dataset(
        args.base, args.tom_root, args.jute_root,
        args.checkpoint, args.out, args.seed,
    )
    print(f"Prepared {len(manifest['classes'])} classes in {args.out}")
    for split, class_counts in manifest["split_counts"].items():
        print(f"{split}: {sum(class_counts.values())} images")
    print(
        "Corrupt images skipped: "
        f"{len(manifest['external_scan']['corrupt_images'])}; exact duplicates removed: "
        f"{manifest['external_scan']['exact_duplicates_removed']}; "
        "cross-source overlaps removed: "
        f"{manifest['external_scan']['exact_overlaps_with_existing_dataset_removed']}"
    )
    print(f"Dataset report: {args.out / 'dataset_manifest.json'}")


if __name__ == "__main__":
    main()
