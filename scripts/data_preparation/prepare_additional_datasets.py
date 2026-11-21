"""Audit and prepare Groundnut, Turmeric, and tomato-pest datasets."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, UnidentifiedImageError
import torch

from .prepare_leaf_extension import (
    IMAGE_EXTENSIONS,
    _deduplicate_base,
    _link_or_copy,
    _read_base_records,
    build_class_mapping,
    split_external_records,
)


ROOT = Path(__file__).resolve().parents[2]
GROUNDNUT_ROOT = (
    ROOT
    / "02 - Groundnut leaf dataset"
    / "A novel groundnut leaf dataset for detection and classification of groundnut leaf diseases"
)
TURMERIC_ROOT = (
    ROOT
    / "05 -  Turmeric Plant Leaf Disease Dataset"
    / "Image Dataset for Turmeric Plant Leaf Disease Detection"
)
TOMATO_PEST_ORIGINAL_ROOT = (
    ROOT / "data" / "tomato_pests_original" / "Original image of tomato pest"
)
TOMATO_PEST_AUGMENTED_ROOT = (
    ROOT / "data" / "tomato_pests_augmented_source" / "Tomato pest image enhancement"
)
BASE_DATA = ROOT / "data" / "leaf_all_crops_v6"
BASE_CHECKPOINT = ROOT / "runs" / "leaf_extension_candidate" / "model.pt"
LEAF_OUTPUT = ROOT / "data" / "leaf_all_crops_v7"
PEST_OUTPUT = ROOT / "data" / "tomato_pests_v1"
REPORT_OUTPUT = ROOT / "data" / "additional_dataset_audit.json"

GROUNDNUT_LABELS = {
    "ALTERNARIA LEAF SPOT": "Groundnut___Alternaria_Leaf_Spot",
    "HEALTHY": "Groundnut___healthy",
    "LEAF SPOT (EARLY AND LATE)": "Groundnut___Leaf_Spot_Early_and_Late",
    "ROSETTE": "Groundnut___Rosette",
    "RUST": "Groundnut___Rust",
}
TURMERIC_LABELS = {
    "Aphids_Disease": "Turmeric___Aphids_Disease",
    "Blotch": "Turmeric___Blotch",
    "Healthy_Leaf": "Turmeric___healthy",
    "Leaf_Spot": "Turmeric___Leaf_Spot",
}
TOMATO_PEST_LABELS = {
    "BA": "BA",
    "HA": "HA",
    "MP": "MP",
    "SE": "SE",
    "SL": "SL",
    "TP": "TP",
    "TU": "TU",
    "ZC": "ZC",
}


def image_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_class_tree(root, labels, dataset_name):
    if not root.is_dir():
        raise FileNotFoundError(f"{dataset_name} directory not found: {root}")

    records, corrupt = [], []
    counts, formats, modes, dimensions = Counter(), Counter(), Counter(), Counter()
    for folder_name, label in labels.items():
        class_root = root / folder_name
        if not class_root.is_dir():
            raise FileNotFoundError(
                f"Expected {dataset_name} class folder not found: {class_root}"
            )
        for path in sorted(class_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            counts[label] += 1
            formats[path.suffix.lower()] += 1
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    size, mode = image.size, image.mode
                digest = image_digest(path)
            except (OSError, ValueError, UnidentifiedImageError) as error:
                corrupt.append({"path": str(path), "error": str(error)})
                continue

            dimensions[f"{size[0]}x{size[1]}"] += 1
            modes[mode] += 1
            relative = path.relative_to(root)
            records.append({
                "path": path,
                "label": label,
                "source": dataset_name,
                "family": f"{dataset_name}:{label}:{path.stem.casefold()}",
                "size": size,
                "mode": mode,
                "digest": digest,
                "relative_path": str(relative),
            })

    digest_groups = defaultdict(list)
    for record in records:
        digest_groups[record["digest"]].append(record)
    duplicate_groups = [
        group for group in digest_groups.values() if len(group) > 1
    ]
    label_conflicts = [
        group for group in duplicate_groups
        if len({record["label"] for record in group}) > 1
    ]
    total = sum(counts.values())
    positive = [count for count in counts.values() if count]
    low_resolution_counts = {
        threshold: sum(
            min(record["size"]) < threshold for record in records
        )
        for threshold in (128, 224)
    }
    return {
        "root": str(root),
        "images": total,
        "readable_images": len(records),
        "classes": len(labels),
        "class_counts": dict(sorted(counts.items())),
        "class_imbalance_ratio": (
            max(positive) / min(positive) if positive else None
        ),
        "formats": dict(sorted(formats.items())),
        "color_modes": dict(sorted(modes.items())),
        "dimensions": dict(sorted(dimensions.items())),
        "images_below_minimum_dimension": low_resolution_counts,
        "corrupt_count": len(corrupt),
        "corrupt_examples": corrupt[:20],
        "unique_image_hashes": len(digest_groups),
        "exact_duplicate_groups": len(duplicate_groups),
        "exact_duplicate_extra_copies": sum(
            len(group) - 1 for group in duplicate_groups
        ),
        "cross_label_duplicate_groups": len(label_conflicts),
        "duplicate_examples": [
            [record["relative_path"] for record in group[:8]]
            for group in duplicate_groups[:20]
        ],
        "records": records,
    }


def public_audit(audit):
    return {key: value for key, value in audit.items() if key != "records"}


def exact_overlap_summary(first, second):
    first_hashes = {record["digest"] for record in first["records"]}
    second_hashes = {record["digest"] for record in second["records"]}
    overlap = first_hashes & second_hashes
    return {
        "shared_exact_image_hashes": len(overlap),
        "unique_images_in_first": len(first_hashes - second_hashes),
        "unique_images_in_second": len(second_hashes - first_hashes),
    }


def clean_new_records(records, base_digests=None):
    base_digests = base_digests or {}
    by_digest = defaultdict(list)
    for record in records:
        by_digest[record["digest"]].append(record)

    kept, duplicate_count = [], 0
    base_overlap_count, ambiguous_count = 0, 0
    duplicate_examples, conflict_examples = [], []
    for digest, group in sorted(by_digest.items()):
        if digest in base_digests:
            base_overlap_count += len(group)
            continue
        labels = {record["label"] for record in group}
        if len(labels) > 1:
            ambiguous_count += 1
            conflict_examples.append(
                [record["relative_path"] for record in group[:8]]
            )
            continue
        duplicate_count += len(group) - 1
        if len(group) > 1:
            duplicate_examples.append(
                [record["relative_path"] for record in group[:8]]
            )
        kept.append(min(group, key=lambda record: str(record["path"])))

    return kept, {
        "exact_duplicates_removed": duplicate_count,
        "ambiguous_duplicate_groups_removed": ambiguous_count,
        "exact_overlaps_with_base_removed": base_overlap_count,
        "duplicate_examples": duplicate_examples[:20],
        "ambiguous_examples": conflict_examples[:20],
    }


def split_records(records, seed):
    assigned, small_classes = split_external_records(records, seed)
    split_by_family = defaultdict(set)
    for record in assigned:
        split_by_family[record["family"]].add(record["split"])
    crossing_families = [
        family for family, splits in split_by_family.items() if len(splits) > 1
    ]
    if crossing_families:
        raise ValueError(
            f"Source-image families crossed splits: {crossing_families[:5]}"
        )
    return assigned, small_classes


def counts_by_split(records):
    counts = {name: Counter() for name in ("train", "validation", "test")}
    for record in records:
        counts[record["split"]][record["label"]] += 1
    return {
        split: dict(sorted(class_counts.items()))
        for split, class_counts in counts.items()
    }


def write_split(records, output_root, prefix_digest=False):
    counts = Counter()
    for record in records:
        name = record["path"].name
        if prefix_digest:
            name = f"{record['digest'][:12]}_{name}"
        destination = (
            output_root / record["split"] / record["label"] / name
        )
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite {destination}")
        _link_or_copy(record["path"], destination)
        counts[(record["split"], record["label"])] += 1
    return counts


def _read_base_digests(base_records):
    result = defaultdict(set)
    for record in base_records:
        result[record["digest"]].add(record["label"])
    return result


def build_datasets(seed=42):
    for output_root in (LEAF_OUTPUT, PEST_OUTPUT):
        if output_root.exists() and any(output_root.iterdir()):
            raise FileExistsError(
                f"Output directory is not empty; refusing to overwrite: "
                f"{output_root}"
            )

    groundnut = audit_class_tree(
        GROUNDNUT_ROOT, GROUNDNUT_LABELS, "groundnut_original"
    )
    turmeric = audit_class_tree(
        TURMERIC_ROOT / "Original DataSet",
        TURMERIC_LABELS,
        "turmeric_original",
    )
    turmeric_augmented = audit_class_tree(
        TURMERIC_ROOT / "Augmented DataSet",
        TURMERIC_LABELS,
        "turmeric_augmented",
    )
    pest_original = audit_class_tree(
        TOMATO_PEST_ORIGINAL_ROOT, TOMATO_PEST_LABELS, "tomato_pest_original"
    )
    pest_augmented = audit_class_tree(
        TOMATO_PEST_AUGMENTED_ROOT,
        TOMATO_PEST_LABELS,
        "tomato_pest_augmented",
    )
    turmeric_overlap = exact_overlap_summary(turmeric, turmeric_augmented)
    pest_archive_overlap = exact_overlap_summary(pest_original, pest_augmented)

    checkpoint = torch.load(BASE_CHECKPOINT, map_location="cpu", weights_only=False)
    base_classes = checkpoint.get("classes")
    if not isinstance(base_classes, list) or not base_classes:
        raise ValueError(f"Checkpoint has no class mapping: {BASE_CHECKPOINT}")
    base_records, base_corrupt = _read_base_records(BASE_DATA, base_classes)
    base_records, base_dedup = _deduplicate_base(base_records)
    base_digests = _read_base_digests(base_records)

    new_leaf_records = groundnut["records"] + turmeric["records"]
    new_leaf_records, leaf_cleanup = clean_new_records(
        new_leaf_records, base_digests
    )
    new_leaf_records, leaf_small_classes = split_records(new_leaf_records, seed)
    pest_records, pest_cleanup = clean_new_records(pest_original["records"])
    pest_records, pest_small_classes = split_records(pest_records, seed)

    leaf_counts = {split: Counter() for split in ("train", "validation", "test")}
    for record in base_records:
        leaf_counts[record["split"]][record["label"]] += 1
    for record in new_leaf_records:
        leaf_counts[record["split"]][record["label"]] += 1

    split_counts = {
        split: dict(sorted(class_counts.items()))
        for split, class_counts in leaf_counts.items()
    }
    leaf_classes, leaf_class_to_idx = build_class_mapping(split_counts)
    if set(base_classes) - set(leaf_classes):
        raise ValueError("The expanded mapping dropped classes from the base model")

    LEAF_OUTPUT.mkdir(parents=True, exist_ok=True)
    PEST_OUTPUT.mkdir(parents=True, exist_ok=True)
    for record in base_records:
        destination = (
            LEAF_OUTPUT / record["split"] / record["label"] / record["path"].name
        )
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite {destination}")
        _link_or_copy(record["path"], destination)
    write_split(new_leaf_records, LEAF_OUTPUT, prefix_digest=True)
    write_split(pest_records, PEST_OUTPUT)

    pest_counts = counts_by_split(pest_records)
    pest_classes, pest_class_to_idx = build_class_mapping(pest_counts)
    if set(pest_classes) != set(TOMATO_PEST_LABELS.values()):
        raise ValueError(
            "The pest train split must contain all eight source categories"
        )

    leaf_manifest = {
        "base_checkpoint": str(BASE_CHECKPOINT),
        "base_data": str(BASE_DATA),
        "seed": seed,
        "split_counts": split_counts,
        "classes": leaf_classes,
        "class_to_idx": leaf_class_to_idx,
        "base_corrupt_images": base_corrupt,
        "base_duplicate_cleanup": base_dedup,
        "new_leaf_cleanup": leaf_cleanup,
        "new_leaf_split_counts": counts_by_split(new_leaf_records),
        "classes_without_held_out_examples": leaf_small_classes,
        "sources": {
            "groundnut": public_audit(groundnut),
            "turmeric_original_used": public_audit(turmeric),
            "turmeric_augmented_excluded": public_audit(turmeric_augmented),
        },
        "augmentation_policy": (
            "Only original source photographs are included. train.py performs "
            "random augmentation on training batches only."
        ),
        "label_notes": {
            "Groundnut___Leaf_Spot_Early_and_Late": (
                "The downloaded source combines early and late leaf spot in one "
                "folder; it is retained as a single class."
            ),
            "Turmeric___Aphids_Disease": (
                "The source labels this category Aphids_Disease. It is retained "
                "verbatim as a turmeric leaf-condition label; it is not merged "
                "into the separate tomato-insect task."
            ),
        },
    }
    pest_manifest = {
        "dataset": "Eight common tomato pest images",
        "classes": pest_classes,
        "class_to_idx": pest_class_to_idx,
        "split_counts": pest_counts,
        "original_source": public_audit(pest_original),
        "augmented_source_excluded": public_audit(pest_augmented),
        "original_vs_augmented_exact_overlap": pest_archive_overlap,
        "duplicate_cleanup": pest_cleanup,
        "classes_without_held_out_examples": pest_small_classes,
        "source_labels": {
            code: {
                "source_folder": code,
                "display_name": f"Tomato pest category {code}",
                "species_mapping_verified": False,
            }
            for code in pest_classes
        },
        "label_notes": (
            "The archive supplies two-letter folder codes only and no taxonomy "
            "or annotation file. Codes are preserved without guessing species."
        ),
        "annotation_notes": (
            "Only image-level folder labels are present; no bounding-box files "
            "or per-image annotations were found."
        ),
        "augmentation_policy": (
            "The pre-augmented archive is audited but excluded from training. "
            "The split uses original photographs only, with online augmentation "
            "applied to the training split."
        ),
    }
    (LEAF_OUTPUT / "dataset_manifest.json").write_text(
        json.dumps(leaf_manifest, indent=2), encoding="utf-8"
    )
    (LEAF_OUTPUT / "class_labels.json").write_text(
        json.dumps(
            {"classes": leaf_classes, "class_to_idx": leaf_class_to_idx},
            indent=2,
        ),
        encoding="utf-8",
    )
    (PEST_OUTPUT / "dataset_manifest.json").write_text(
        json.dumps(pest_manifest, indent=2), encoding="utf-8"
    )
    (PEST_OUTPUT / "class_labels.json").write_text(
        json.dumps(
            {"classes": pest_classes, "class_to_idx": pest_class_to_idx},
            indent=2,
        ),
        encoding="utf-8",
    )

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "groundnut": public_audit(groundnut),
        "turmeric_original": public_audit(turmeric),
        "turmeric_augmented": public_audit(turmeric_augmented),
        "turmeric_original_vs_augmented_exact_overlap": turmeric_overlap,
        "tomato_pest_original": public_audit(pest_original),
        "tomato_pest_augmented": public_audit(pest_augmented),
        "tomato_pest_original_vs_augmented_exact_overlap": pest_archive_overlap,
        "leaf_training": {
            "class_count": len(leaf_classes),
            "split_counts": split_counts,
            "new_class_labels": sorted(
                set(GROUNDNUT_LABELS.values()) | set(TURMERIC_LABELS.values())
            ),
            "cleanup": leaf_cleanup,
            "base_data": str(BASE_DATA),
            "output": str(LEAF_OUTPUT),
        },
        "pest_training": {
            "class_count": len(pest_classes),
            "classes": pest_classes,
            "split_counts": pest_counts,
            "cleanup": pest_cleanup,
            "output": str(PEST_OUTPUT),
        },
    }
    REPORT_OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = build_datasets(args.seed)
    print(f"Dataset report: {REPORT_OUTPUT}")
    print(
        f"Leaf dataset: {report['leaf_training']['class_count']} classes, "
        + ", ".join(
            f"{split}={sum(counts.values())}"
            for split, counts in report["leaf_training"]["split_counts"].items()
        )
    )
    print(
        f"Tomato pest dataset: {report['pest_training']['class_count']} classes, "
        + ", ".join(
            f"{split}={sum(counts.values())}"
            for split, counts in report["pest_training"]["split_counts"].items()
        )
    )


if __name__ == "__main__":
    main()
