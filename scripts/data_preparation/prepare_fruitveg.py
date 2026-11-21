"""Create a deterministic, stratified train/validation/test split for FruitVeg."""

import argparse
import random
import shutil
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=r"data\fruitveg_raw",
                        help="Extracted dataset folder with one subfolder per class")
    parser.add_argument("--out", default=r"data\fruitveg",
                        help="Output folder for train/, validation/, and test/")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    source, output = Path(args.source), Path(args.out)
    if not source.is_dir():
        parser.error(f"Dataset folder does not exist: {source}")
    if output.exists() and any(output.iterdir()):
        parser.error(f"Output folder is not empty: {output}")

    class_dirs = sorted(path for path in source.iterdir() if path.is_dir())
    if not class_dirs:
        parser.error(f"No class folders found in: {source}")

    counts = {"train": 0, "validation": 0, "test": 0}
    for class_index, class_dir in enumerate(class_dirs):
        images = sorted(path for path in class_dir.rglob("*")
                        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS)
        if len(images) < 3:
            parser.error(f"Class {class_dir.name} has fewer than 3 images")
        rng_class = random.Random(args.seed + class_index)
        rng_class.shuffle(images)
        test_count = max(1, round(len(images) * 0.1))
        validation_count = max(1, round(len(images) * 0.1))
        splits = {
            "train": images[:len(images) - test_count - validation_count],
            "validation": images[len(images) - test_count - validation_count:-test_count],
            "test": images[-test_count:],
        }

        for split, split_images in splits.items():
            destination = output / split / class_dir.name
            destination.mkdir(parents=True, exist_ok=True)
            for image in split_images:
                target = destination / image.name
                try:
                    image.hardlink_to(target)
                except OSError:
                    shutil.copy2(image, target)
            counts[split] += len(split_images)

    print(f"Prepared {len(class_dirs)} classes at {output.resolve()}")
    print(", ".join(f"{split}={count}" for split, count in counts.items()))


if __name__ == "__main__":
    main()
