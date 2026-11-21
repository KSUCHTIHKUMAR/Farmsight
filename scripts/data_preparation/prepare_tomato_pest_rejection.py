"""Add independent non-pest examples so pest inference can abstain."""

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
PEST_DATA = ROOT / "data" / "tomato_pests_v1"
LEAF_DATA = ROOT / "data" / "leaf_all_crops_v6"
PRODUCE_DATA = ROOT / "data" / "fruitveg"
REJECTION_LABEL = "Not_Tomato_Pest"
AUDIT_REPORT = ROOT / "data" / "additional_dataset_audit.json"
IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


def image_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_rejection_examples(
    pest_data=PEST_DATA,
    leaf_data=LEAF_DATA,
    produce_data=PRODUCE_DATA,
    seed=42,
):
    mapping_path = pest_data / "class_labels.json"
    manifest_path = pest_data / "dataset_manifest.json"
    labels = json.loads(mapping_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if REJECTION_LABEL in labels["classes"]:
        raise FileExistsError(
            f"The rejection class already exists in {mapping_path}"
        )

    positive_digests = set()
    for split in ("train", "validation", "test"):
        for folder in (pest_data / split).iterdir():
            if not folder.is_dir():
                continue
            for path in folder.iterdir():
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    positive_digests.add(image_digest(path))

    rng = random.Random(seed)
    split_counts = {}
    source_counts = Counter()
    all_negative_digests = set()
    for split in ("train", "validation", "test"):
        target_count = sum(manifest["split_counts"][split].values())
        candidates = []
        for source_name, source_root in (
            ("leaf", leaf_data),
            ("produce", PRODUCE_DATA),
        ):
            split_name = "validation" if split == "validation" else split
            split_root = source_root / split_name
            if not split_root.is_dir() and split == "validation":
                split_root = source_root / "val"
            if not split_root.is_dir():
                raise FileNotFoundError(
                    f"Missing {source_name} {split} split: {split_root}"
                )
            candidates.extend(
                (path, source_name)
                for path in split_root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
            )
        rng.shuffle(candidates)

        selected, seen = [], positive_digests | all_negative_digests
        for path, source_name in candidates:
            try:
                with Image.open(path) as image:
                    image.verify()
                digest = image_digest(path)
            except (OSError, ValueError, UnidentifiedImageError):
                continue
            if digest in seen:
                continue
            seen.add(digest)
            all_negative_digests.add(digest)
            selected.append((path, source_name, digest))
            if len(selected) == target_count:
                break
        if len(selected) != target_count:
            raise ValueError(
                f"Only {len(selected)} clean negative images available for "
                f"{split}; need {target_count}"
            )

        for path, source_name, digest in selected:
            destination = (
                pest_data / split / REJECTION_LABEL
                / f"{source_name}_{digest[:12]}_{path.name}"
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(f"Refusing to overwrite {destination}")
            try:
                destination.hardlink_to(path)
            except OSError:
                import shutil

                shutil.copy2(path, destination)
            source_counts[f"{split}:{source_name}"] += 1
        split_counts[split] = target_count

    classes = sorted([*labels["classes"], REJECTION_LABEL])
    class_to_idx = {label: index for index, label in enumerate(classes)}
    labels.update({"classes": classes, "class_to_idx": class_to_idx})
    for split, count in split_counts.items():
        manifest["split_counts"][split][REJECTION_LABEL] = count
        manifest["split_counts"][split] = dict(
            sorted(manifest["split_counts"][split].items())
        )
    manifest.update({
        "classes": classes,
        "class_to_idx": class_to_idx,
        "reject_class": REJECTION_LABEL,
        "reject_split_counts": split_counts,
        "reject_image_sources": dict(sorted(source_counts.items())),
        "reject_policy": (
            "The classifier includes held-out leaf and produce examples as an "
            "explicit non-target class. It can reject these represented image "
            "types; this is not a guarantee for every unknown image."
        ),
    })
    mapping_path.write_text(json.dumps(labels, indent=2), encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if pest_data.resolve() == PEST_DATA.resolve():
        update_dataset_report(manifest)
    return manifest


def update_dataset_report(manifest=None):
    if not AUDIT_REPORT.is_file():
        return
    report = json.loads(AUDIT_REPORT.read_text(encoding="utf-8"))
    if manifest is None:
        manifest = json.loads(
            (PEST_DATA / "dataset_manifest.json").read_text(encoding="utf-8")
        )
    pest_training = report["pest_training"]
    pest_training.update({
        "class_count": len(manifest["classes"]),
        "classes": manifest["classes"],
        "split_counts": manifest["split_counts"],
        "reject_class": REJECTION_LABEL,
        "reject_split_counts": manifest.get("reject_split_counts", {}),
        "reject_image_sources": manifest.get("reject_image_sources", {}),
    })

    def image_hashes(root):
        return {
            image_digest(path)
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        }

    original_hashes = image_hashes(
        ROOT / "data" / "tomato_pests_original" / "Original image of tomato pest"
    )
    augmented_hashes = image_hashes(
        ROOT / "data" / "tomato_pests_augmented_source"
        / "Tomato pest image enhancement"
    )
    overlap = {
        "shared_exact_image_hashes": len(original_hashes & augmented_hashes),
        "unique_images_in_original": len(original_hashes - augmented_hashes),
        "unique_images_in_augmented": len(augmented_hashes - original_hashes),
    }
    report["tomato_pest_original_vs_augmented_exact_overlap"] = overlap
    report["pest_training"]["original_vs_augmented_exact_overlap"] = overlap
    report["pest_training"]["non_target_rejection"] = manifest.get(
        "reject_policy"
    )
    turmeric_original_hashes = image_hashes(
        Path(report["turmeric_original"]["root"])
    )
    turmeric_augmented_hashes = image_hashes(
        Path(report["turmeric_augmented"]["root"])
    )
    report["turmeric_original_vs_augmented_exact_overlap"] = {
        "shared_exact_image_hashes": len(
            turmeric_original_hashes & turmeric_augmented_hashes
        ),
        "unique_images_in_original": len(
            turmeric_original_hashes - turmeric_augmented_hashes
        ),
        "unique_images_in_augmented": len(
            turmeric_augmented_hashes - turmeric_original_hashes
        ),
    }
    AUDIT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Refresh archive-overlap summary without changing prepared splits",
    )
    args = parser.parse_args()
    if args.audit_only:
        update_dataset_report()
        print(f"Refreshed audit report: {AUDIT_REPORT}")
        return
    manifest = add_rejection_examples(seed=args.seed)
    print(
        "Added non-pest rejection examples: "
        + ", ".join(
            f"{split}={count}"
            for split, count in manifest["reject_split_counts"].items()
        )
    )
    print(f"Classes: {', '.join(manifest['classes'])}")


if __name__ == "__main__":
    main()
